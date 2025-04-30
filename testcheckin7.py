import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect("checkins.db")
cursor = conn.cursor()

base_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)

for i in range(7):
    checkin_time = (base_time - timedelta(days=i)).isoformat()
    checkout_time = (base_time - timedelta(days=i) + timedelta(hours=8)).isoformat()
    
    cursor.execute('''
        INSERT INTO checkins (employee_id, checkin_time, checkout_time, latitude, longitude, context)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        "EMP001", checkin_time, checkout_time, 19.07, 72.88, "Testing history"
    ))

conn.commit()
conn.close()

