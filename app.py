from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import sqlite3
import os

app = FastAPI()

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
        checkout_dt = datetime.fromisoformat(checkout)
        duration = (checkout_dt - checkin_dt).total_seconds() / 3600
        day_of_week = checkin_dt.strftime("%A")
        date = checkin_dt.date()

        if emp_id not in insights:
            insights[emp_id] = []

        insights[emp_id].append({
            "date": date,
            "checkin_hour": checkin_dt.hour,
            "duration_hours": round(duration, 2),
            "context": context.split(",") if context else []
        })

    nudges = []
    for emp_id, logs in insights.items():
        late_count = sum(1 for log in logs if log["checkin_hour"] > 9)  # after 9:00 AM
        long_shift_count = sum(1 for log in logs if log["duration_hours"] > 10)
        avg_hours = sum(log["duration_hours"] for log in logs) / len(logs)

        nudge_text = ""
        if late_count >= 2:
            nudge_text += f"{late_count} late check-ins detected. Review morning shift timings. "
        if long_shift_count >= 2:
            nudge_text += f"{long_shift_count} long shifts (>10h) detected. Watch for burnout. "
        if not nudge_text:
            nudge_text = "No major concerns. Team behavior looks consistent."

        nudges.append({
            "employee_id": emp_id,
            "avg_daily_hours": round(avg_hours, 2),
            "nudges": nudge_text.strip()
        })

    return {"nudges": nudges}
