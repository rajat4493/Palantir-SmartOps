from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import sqlite3
import os
import requests
from engine.models.nudges import generate_nudges
from engine.models.forecast_main import router as forecast_router
from engine.models.riskradar import router as risk_router

app = FastAPI()

templates = Jinja2Templates(directory="../frontend/templates")

DB_FILE = "../db/checkins.db"

##########ADDING THE BURNOUT PART########################################

app.include_router(risk_router)

########################################################################


#####API for Geo Location, we are using OpenCage(https://opencagedata.com)

OPENCAGE_API_KEY = "506c9ae25ba84de0a447d82bcae9f147"

def reverse_geocode(lat, lon):
    try:
        url = f"https://api.opencagedata.com/geocode/v1/json?q={lat}+{lon}&key={OPENCAGE_API_KEY}"
        response = requests.get(url)
        if response.status_code == 200:
            results = response.json()
            if results['results']:
                return results['results'][0]['formatted']  # Full address
    except Exception as e:
        print(f"Reverse geocoding failed: {e}")
    return "Unknown Location"

#######################################################################################################

# Initialize DB (basic setup)
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT,
            checkin_time TEXT,
            checkout_time TEXT,
            latitude REAL,
            longitude REAL,
            context TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Pydantic model for input
class CheckIn(BaseModel):
    employee_id: str
    checkin_time: datetime
    checkout_time: datetime
    context: Optional[List[str]] = []

# Endpoint to submit check-in
@app.post("/checkin")
def submit_checkin(data: CheckIn):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO checkins (employee_id, checkin_time, checkout_time, context)
        VALUES (?, ?, ?, ?)
    ''', (data.employee_id, data.checkin_time.isoformat(), data.checkout_time.isoformat(), ",".join(data.context)))
    conn.commit()
    conn.close()
    return {"message": "Check-in recorded"}

####Adding the checkin form - HTML input form 

@app.get("/checkin-form", response_class=HTMLResponse)
async def checkin_form(request: Request):
    return templates.TemplateResponse("checkin_form.html", {"request": request})

@app.post("/submit-checkin")
async def submit_checkin_form(
    employee_id: str = Form(...),
    latitude: float = Form(None),
    longitude: float = Form(None)
):
    from datetime import datetime
    checkin_time = datetime.now()
    location_name = reverse_geocode(latitude, longitude)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO checkins (employee_id, checkin_time, checkout_time, latitude, longitude, context)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        employee_id,
        checkin_time.isoformat(),
        None,
        latitude,
        longitude,
        location_name
    ))
    conn.commit()
    conn.close()

    return RedirectResponse(url="/checkin-form", status_code=303)

#####Adding the check out time with checkout time format form
@app.get("/checkout-form", response_class=HTMLResponse)
async def checkout_form(request: Request):
    return templates.TemplateResponse("checkout_form.html", {"request": request})

@app.post("/submit-checkout")
async def submit_checkout_form(employee_id: str = Form(...)):
    from datetime import datetime

    checkout_time = datetime.now()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Find the latest record for this employee with NULL checkout
    cursor.execute('''
        SELECT id FROM checkins
        WHERE employee_id = ? AND checkout_time IS NULL
        ORDER BY checkin_time DESC
        LIMIT 1
    ''', (employee_id,))
    result = cursor.fetchone()

    if result:
        checkin_id = result[0]
        cursor.execute('''
            UPDATE checkins
            SET checkout_time = ?
            WHERE id = ?
        ''', (checkout_time.isoformat(), checkin_id))
        conn.commit()

    conn.close()

    return RedirectResponse(url="/checkout-form", status_code=303)

###################################################################################################################################

# Endpoint to get behavior timeline for an employee
@app.get("/timeline/{employee_id}")
def get_behavior_timeline(employee_id: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT checkin_time, checkout_time, context FROM checkins
        WHERE employee_id = ?
        ORDER BY checkin_time ASC
    ''', (employee_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No check-in records found for this employee.")

    timeline = []
    for checkin, checkout, context in rows:
        checkin_dt = datetime.fromisoformat(checkin)
        checkout_dt = datetime.fromisoformat(checkout)
        duration = (checkout_dt - checkin_dt).total_seconds() / 3600
        timeline.append({
            "date": checkin_dt.date().isoformat(),
            "checkin": checkin_dt.time().strftime("%H:%M"),
            "checkout": checkout_dt.time().strftime("%H:%M"),
            "duration_hours": round(duration, 2),
            "context": context.split(",") if context else []
        })

    return {"employee_id": employee_id, "timeline": timeline}

############ CALCULATE personalized baseline for each employee to see the pattern ###################

def calculate_baseline(employee_id, conn):
    cursor = conn.cursor()
    cursor.execute('''
        SELECT checkin_time FROM checkins
        WHERE employee_id = ?
        AND checkin_time IS NOT NULL
        ORDER BY checkin_time DESC
        LIMIT 7
    ''', (employee_id,))
    
    times = []
    for row in cursor.fetchall():
        dt = datetime.fromisoformat(row[0])
        minutes = dt.hour * 60 + dt.minute
        times.append(minutes)
    
    if not times:
        return None, None

    mean = sum(times) / len(times)
    stddev = (sum((x - mean) ** 2 for x in times) / len(times)) ** 0.5
    return mean, stddev

############################


################Adding the behaviour shift detection########################################

def detect_shift(employee_id, conn):
    cursor = conn.cursor()

    # Get last 3 check-ins
    cursor.execute('''
        SELECT checkin_time FROM checkins
        WHERE employee_id = ?
        AND checkin_time IS NOT NULL
        ORDER BY checkin_time DESC
        LIMIT 3
    ''', (employee_id,))
    recent = [
        datetime.fromisoformat(row[0]).hour * 60 + datetime.fromisoformat(row[0]).minute
        for row in cursor.fetchall()
    ]

    # Get baseline (older)
    cursor.execute('''
        SELECT checkin_time FROM checkins
        WHERE employee_id = ?
        AND checkin_time IS NOT NULL
        ORDER BY checkin_time DESC
        LIMIT 7 OFFSET 3
    ''', (employee_id,))
    baseline = [
        datetime.fromisoformat(row[0]).hour * 60 + datetime.fromisoformat(row[0]).minute
        for row in cursor.fetchall()
    ]

    if len(recent) < 2 or len(baseline) < 3:
        return None

    avg_recent = sum(recent) / len(recent)
    avg_baseline = sum(baseline) / len(baseline)
    diff = avg_recent - avg_baseline

    return diff  # + means later, - means earlier

#################Getting forecast from forecast.py############

app.include_router(forecast_router)

#####################################
@app.get("/nudges")
def nudges_route():
    return generate_nudges()
