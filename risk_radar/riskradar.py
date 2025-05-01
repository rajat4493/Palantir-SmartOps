from datetime import datetime, timedelta
import sqlite3
from fastapi import APIRouter, Query
from typing import List

router = APIRouter()
DB_FILE = "checkins.db"

@router.get("/risk-radar")
def risk_radar(employees: List[str] = Query(...)):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    today = datetime.now().date()
    start_date = today - timedelta(days=14)

    risks = []

    for emp_id in employees:
        cursor.execute('''
            SELECT checkin_time, checkout_time FROM checkins
            WHERE employee_id = ? AND DATE(checkin_time) BETWEEN ? AND ?
            ORDER BY checkin_time ASC
        ''', (emp_id, start_date.isoformat(), today.isoformat()))

        records = cursor.fetchall()
        if not records:
            risks.append({
                "employee_id": emp_id,
                "risk_type": "Attendance Gap",
                "signal": "No check-ins in last 14 days",
                "recommendation": "Reach out personally",
                "severity": "high"
            })
            continue

        total_hours = 0
        work_days = 0
        shift_deltas = []
        missing_checkout = 0

        for checkin_str, checkout_str in records:
            checkin = datetime.fromisoformat(checkin_str)
            work_days += 1

            # Burnout and reliability
            if checkout_str:
                checkout = datetime.fromisoformat(checkout_str)
                hours = (checkout - checkin).total_seconds() / 3600.0
                total_hours += hours
            else:
                missing_checkout += 1
                continue

            # Unpredictability: deviation from 9:00 am
            shift_delta = abs((checkin.hour * 60 + checkin.minute) - (9 * 60))
            shift_deltas.append(shift_delta)

        avg_hours = total_hours / work_days if work_days else 0
        stddev_shift = (sum((x - sum(shift_deltas)/len(shift_deltas)) ** 2 for x in shift_deltas) / len(shift_deltas)) ** 0.5 if shift_deltas else 0

        # Burnout Risk
        if avg_hours > 9:
            risks.append({
                "employee_id": emp_id,
                "risk_type": "Burnout",
                "signal": f"Avg {avg_hours:.1f} hrs/day over last 14 days",
                "recommendation": "Suggest cooldown periods or support",
                "severity": "high"
            })

        # Unpredictability
        if stddev_shift > 90:
            risks.append({
                "employee_id": emp_id,
                "risk_type": "Unpredictability",
                "signal": f"Avg check-in variance: {int(stddev_shift)} mins",
                "recommendation": "Suggest routine alignment",
                "severity": "medium"
            })

        # Missing Checkout risk
        if missing_checkout >= 3:
            risks.append({
                "employee_id": emp_id,
                "risk_type": "Missing Checkouts",
                "signal": f"{missing_checkout} days missing checkout",
                "recommendation": "Follow-up on process",
                "severity": "low"
            })

    conn.close()
    return {"risks": risks}

