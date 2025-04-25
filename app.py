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

# Endpoint to get attendance insights
@app.get("/nudges")
def get_nudges():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT employee_id, checkin_time, checkout_time, context FROM checkins
    ''')
    rows = cursor.fetchall()
    conn.close()

    insights = {}
    for emp_id, checkin, checkout, context in rows:
        checkin_dt = datetime.fromisoformat(checkin)
        checkout_dt = datetime.fromisoformat(checkout)
        duration = (checkout_dt - checkin_dt).total_seconds() / 3600
        key = f"{emp_id}"
        if key not in insights:
            insights[key] = []
        insights[key].append({"date": checkin_dt.date().isoformat(), "duration_hours": round(duration, 2), "context": context.split(",")})

    # Generate simple nudge logic
    nudges = []
    for emp, logs in insights.items():
        late_days = sum(1 for log in logs if datetime.fromisoformat(log['date']).weekday() < 5 and datetime.strptime(log['date'], '%Y-%m-%d').day < 10)
        avg_duration = sum(log['duration_hours'] for log in logs) / len(logs)
        nudges.append({
            "employee_id": emp,
            "late_days": late_days,
            "avg_daily_hours": round(avg_duration, 2),
            "note": "Consider adjusting workload" if avg_duration > 10 else "All good"
        })

    return {"nudges": nudges}

