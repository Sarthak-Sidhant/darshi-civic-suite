import requests
import random
import time

URL = "http://127.0.0.1:8000/api/v1/report"

# A specific location in Bangalore (The "Crisis Zone")
CRISIS_LAT = 12.9716
CRISIS_LNG = 77.5946

# Dummy user IDs
users = ["citizen_A", "citizen_B", "citizen_C", "citizen_D", "citizen_E","citizen_A", "citizen_B", "citizen_C", "citizen_D", "citizen_E","citizen_A", "citizen_B", "citizen_C", "citizen_D", "citizen_E","citizen_A", "citizen_B", "citizen_C", "citizen_D", "citizen_E","citizen_A", "citizen_B", "citizen_C", "citizen_D", "citizen_E","citizen_A", "citizen_B", "citizen_C", "citizen_D", "citizen_E","citizen_A", "citizen_B", "citizen_C", "citizen_D", "citizen_E","citizen_A", "citizen_B", "citizen_C", "citizen_D", "citizen_E"]

print("🚨 Simulating a Civic Crisis (Flood in Bangalore)...")

for user in users:
    # Add tiny random variation to location so they aren't EXACTLY on top of each other
    # but close enough for the logic to group them.
    lat = CRISIS_LAT + random.uniform(-0.000000000000001, 0.00000000000000000001)
    lng = CRISIS_LNG + random.uniform(-0.0000000000000000001, 0.0000000001)
    
    payload = {
        "location": f"{lat}, {lng}",
        "user_id": user
    }
    
    # We use the same pothole image, assuming AI classifies it as high severity
    # OR you can temporarily mock the AI response in code if you want to save API costs.
    files = [
        ('file', ('pothole.jpg', open('pothole.jpg', 'rb'), 'image/jpeg'))
    ]
    
    print(f" -> Submitting report for {user} at {lat:.4f}, {lng:.4f}")
    requests.post(URL, data=payload, files=files)
    time.sleep(1) # Sleep to not overwhelm local server

print("✅ Crisis Data Injected.")