from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import sqlite3
import os

app = FastAPI()

templates = Jinja2Templates(directory="templates")

DB_FILE = "checkins.db"

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
async def submit_checkin_form(employee_id: str = Form(...)):
    from datetime import datetime

    checkin_time = datetime.now()
    checkout_time = None  # We use same time for now; later will handle real checkout

    # Insert into DB just like API
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO checkins (employee_id, checkin_time, checkout_time, context)
        VALUES (?, ?, ?, ?)
    ''', (employee_id, checkin_time.isoformat(), None, ""))
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

# Endpoint to generate smart nudges
@app.get("/nudges")
def generate_nudges():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT employee_id, checkin_time, checkout_time, context FROM checkins
    ''')
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {"nudges": []}

    insights = {}
    for emp_id, checkin, checkout, context in rows:
        checkin_dt = datetime.fromisoformat(checkin)
        checkout_dt = datetime.fromisoformat(checkout) if checkout else None
        duration = (checkout_dt - checkin_dt).total_seconds() / 3600 if checkout else 0
        day_of_week = checkin_dt.strftime("%A")
        date = checkin_dt.date()

        if emp_id not in insights:
            insights[emp_id] = []

        insights[emp_id].append({
            "date": date,
            "checkin_hour": checkin_dt.hour,
            "duration_hours": round(duration, 2),
            "checkout_missing": checkout is None,
            "context": context.split(",") if context else []
        })

    nudges = []
    for emp_id, logs in insights.items():
        late_count = sum(1 for log in logs if log["checkin_hour"] > 9)
        early_leave_count = sum(1 for log in logs if log["duration_hours"] < 6 and log["duration_hours"] > 0)
        long_shift_count = sum(1 for log in logs if log["duration_hours"] > 10)
        missing_checkout_count = sum(1 for log in logs if log["checkout_missing"])
        avg_hours = sum(log["duration_hours"] for log in logs if log["duration_hours"] > 0) / len(logs)

        # Build nudge message
        messages = []
        if late_count > 0:
            messages.append(f"{late_count} late check-ins")
        if early_leave_count > 0:
            messages.append(f"{early_leave_count} early leaves")
        if long_shift_count > 0:
            messages.append(f"{long_shift_count} long shifts (>10h)")
        if missing_checkout_count > 0:
            messages.append(f"{missing_checkout_count} missing checkouts")

        if not messages:
            nudge_msg = "No major concerns. Team behavior looks consistent."
            severity = "low"
        else:
            nudge_msg = ", ".join(messages) + " detected. Recommend review."
            if long_shift_count >= 3 or late_count >= 3:
                severity = "medium"
            else:
                severity = "low"

        nudges.append({
            "employee_id": emp_id,
            "summary": {
                "late_checkins": late_count,
                "early_leaves": early_leave_count,
                "long_shifts": long_shift_count,
                "missing_checkouts": missing_checkout_count,
                "avg_daily_hours": round(avg_hours, 2)
            },
            "nudge_message": nudge_msg,
            "severity": severity
        })

    return {"nudges": nudges}
