import random
from datetime import datetime, timedelta
import requests

# Configuration
employees = ["EMP001", "EMP002", "EMP003", "EMP004", "EMP005"]
address = "Cedrowa 27, 80-126 Gdańsk, Poland"
base_lat = 54.3382
base_lon = 18.5858

# Generate check-in and check-out with scenarios
def generate_checkin_checkout(day_offset):
    base_day = datetime.now() - timedelta(days=day_offset)
    checkin_time = base_day.replace(hour=9, minute=random.randint(0, 59), second=random.randint(0, 59))

    scenario = random.choice(["normal", "late_checkin", "early_checkout", "missing_checkout", "long_shift", "short_shift"])
    
    if scenario == "normal":
        checkout_time = checkin_time + timedelta(hours=8)
    elif scenario == "late_checkin":
        checkin_time = checkin_time.replace(hour=random.randint(10, 12))
        checkout_time = checkin_time + timedelta(hours=8)
    elif scenario == "early_checkout":
        checkout_time = checkin_time + timedelta(hours=5)
    elif scenario == "long_shift":
        checkout_time = checkin_time + timedelta(hours=10)
    elif scenario == "short_shift":
        checkout_time = checkin_time + timedelta(hours=3)
    else:
        checkout_time = checkin_time + timedelta(hours=8)

    return checkin_time, checkout_time

# Generate and print data
record_id = 1
for day in range(10):
    for emp in employees:
        checkin, checkout = generate_checkin_checkout(day_offset=day)
        lat = base_lat + random.uniform(-0.0002, 0.0002)
        lon = base_lon + random.uniform(-0.0002, 0.0002)
        
        print(f"{record_id}|{emp}|{checkin.isoformat()}|{checkout.isoformat()}|{lat}|{lon}|{address}")
        record_id += 1

        # Optional: send via POST
        payload = {
             "employee_id": emp,
             "checkin_time": checkin.isoformat(),
             "checkout_time": checkout.isoformat(),
             "latitude": lat,
             "longitude": lon,
             "address": address
         }
        response = requests.post("http://127.0.0.1:8000/checkin", json=payload)
        print(f"Sent {record_id}: {response.status_code}")
