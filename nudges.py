from datetime import datetime
import sqlite3

DB_FILE = "checkins.db"

def minutes_since_midnight(dt: datetime):
    return dt.hour * 60 + dt.minute

def calculate_baseline(employee_id, conn):
    cursor = conn.cursor()
    cursor.execute('''
        SELECT checkin_time FROM checkins
        WHERE employee_id = ?
        AND checkin_time IS NOT NULL
        ORDER BY checkin_time DESC
        LIMIT 7
    ''', (employee_id,))

    times = [minutes_since_midnight(datetime.fromisoformat(row[0])) for row in cursor.fetchall()]

    if not times:
        return None, None

    mean = sum(times) / len(times)
    stddev = (sum((x - mean) ** 2 for x in times) / len(times)) ** 0.5
    return mean, stddev

def detect_shift(employee_id, conn):
    cursor = conn.cursor()

    # Recent 3 check-ins
    cursor.execute('''
        SELECT checkin_time FROM checkins
        WHERE employee_id = ?
        AND checkin_time IS NOT NULL
        ORDER BY checkin_time DESC
        LIMIT 3
    ''', (employee_id,))
    recent = [minutes_since_midnight(datetime.fromisoformat(row[0])) for row in cursor.fetchall()]

    # Baseline (prior 7 - 3 = 4 days)
    cursor.execute('''
        SELECT checkin_time FROM checkins
        WHERE employee_id = ?
        AND checkin_time IS NOT NULL
        ORDER BY checkin_time DESC
        LIMIT 7 OFFSET 3
    ''', (employee_id,))
    baseline = [minutes_since_midnight(datetime.fromisoformat(row[0])) for row in cursor.fetchall()]

    if len(recent) < 2 or len(baseline) < 3:
        return None

    avg_recent = sum(recent) / len(recent)
    avg_baseline = sum(baseline) / len(baseline)
    return avg_recent - avg_baseline

def generate_nudges():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT employee_id FROM checkins')
    employees = [row[0] for row in cursor.fetchall()]

    nudges = []

    for employee_id in employees:
        # Get today's check-in
        today = datetime.now().date()
        cursor.execute('''
            SELECT checkin_time FROM checkins
            WHERE employee_id = ? AND DATE(checkin_time) = ?
        ''', (employee_id, today.isoformat()))
        row = cursor.fetchone()

        if row:
            checkin_dt = datetime.fromisoformat(row[0])
            checkin_minutes = minutes_since_midnight(checkin_dt)
            mean, stddev = calculate_baseline(employee_id, conn)

            if mean and abs(checkin_minutes - mean) > max(30, stddev * 1.5):
                nudges.append({
                    "employee_id": employee_id,
                    "summary": "Unusual check-in",
                    "nudge_message": f"Checked in at {checkin_dt.strftime('%H:%M')}, usual is ~{int(mean//60):02d}:{int(mean%60):02d}.",
                    "severity": "yellow"
                })

        # Behavior shift
        shift = detect_shift(employee_id, conn)
        if shift and abs(shift) > 30:
            direction = "later" if shift > 0 else "earlier"
            nudges.append({
                "employee_id": employee_id,
                "summary": "Behavior Shift",
                "nudge_message": f"Check-in shifted {int(abs(shift))} mins {direction} over recent days.",
                "severity": "yellow"
            })

    conn.close()
    return {"nudges": nudges}

