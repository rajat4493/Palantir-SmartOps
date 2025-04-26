import requests
import random
from datetime import datetime, timedelta

# Settings
url = "http://127.0.0.1:8000/checkin"
num_records = 300  # how many checkins you want to create

employees = ["EMP001", "EMP002", "EMP003", "EMP004", "EMP005"]
contexts = ["rain", "sunny", "snow", "cloudy", "windy", "fog", "storm"]

# Scenario Probabilities
def generate_checkin_checkout():
    base_day = datetime.now() - timedelta(days=random.randint(1, 10))
    
    # Base checkin time
    checkin_time = base_day.replace(hour=9, minute=random.randint(0, 59), second=0)

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

    return checkin_time, checkout_time, scenario

# Create and send records
for i in range(num_records):
    employee_id = random.choice(employees)
    checkin_time, checkout_time, scenario = generate_checkin_checkout()
    selected_contexts = random.sample(contexts, k=random.randint(1, 2))

    payload = {
        "employee_id": employee_id,
        "checkin_time": checkin_time.isoformat(),
        "checkout_time": checkout_time.isoformat() if checkout_time else None,
        "context": selected_contexts
    }

    response = requests.post(url, json=payload)
    print(f"Record {i+1} ({scenario}) -> Status {response.status_code}: {response.text}")

