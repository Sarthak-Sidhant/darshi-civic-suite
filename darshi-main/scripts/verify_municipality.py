"""
Verification Script for Municipality Workflow
Usage: python3 -m scripts.verify_municipality
"""
import asyncio
import httpx
import logging
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify")

BASE_URL = "http://localhost:8080/api/v1"

# Test Credentials (matches create_official example)
ADMIN_USER = "ranchi_admin"
ADMIN_PASS = "securepass123"

# Coordinates
RANCHI_COORDS = {"lat": 23.3441, "lng": 85.3096}
FAR_AWAY_COORDS = {"lat": 51.5074, "lng": -0.1278} # London

async def get_token(username, password):
    async with httpx.AsyncClient() as client:
        # Assuming standard OAuth2 login endpoint
        response = await client.post(
            f"{BASE_URL}/auth/login",
            data={"username": username, "password": password}
        )
        if response.status_code != 200:
            logger.error(f"Login failed: {response.text}")
            return None
        return response.json()["access_token"]

async def verify_dashboard(token):
    logger.info("Verifying Admin Dashboard Access...")
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/municipality/dashboard",
            headers=headers
        )
        if response.status_code == 200:
            logger.info("✅ Dashboard Access: SUCCESS")
            stats = response.json()
            logger.info(f"   Stats: {stats}")
            return True
        else:
            logger.error(f"❌ Dashboard Access: FAILED ({response.status_code})")
            logger.error(response.text)
            return False

async def create_report(token, lat, lng, description="Test Report"):
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "title": "Test Report",
        "description": description,
        "category": "road",
        "latitude": lat,
        "longitude": lng,
        "address": "Test Location"
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/reports",
            json=data,
            headers=headers
        )
        if response.status_code == 201:
            return response.json()
        logger.error(f"Report creation failed: {response.text}")
        return None

async def verify_auto_assignment():
    logger.info("Verifying Report Auto-Assignment...")
    
    # We need a citizen token for report creation. 
    # For this test, we might need to register a temp user or use the admin token if admins can create reports.
    # Let's try to register a temp user first.
    temp_user = f"test_citizen_{int(asyncio.get_event_loop().time())}"
    temp_pass = "testpass123"
    
    async with httpx.AsyncClient() as client:
        # Register
        logger.info(f"Registering temp citizen: {temp_user}")
        await client.post(f"{BASE_URL}/auth/register", json={
            "username": temp_user,
            "email": f"{temp_user}@example.com",
            "password": temp_pass
        })
    
    token = await get_token(temp_user, temp_pass)
    if not token:
        logger.error("❌ Could not get citizen token. Aborting.")
        return

    # 1. Test Ranchi
    logger.info(f"Creating report in Ranchi {RANCHI_COORDS}...")
    report1 = await create_report(token, RANCHI_COORDS['lat'], RANCHI_COORDS['lng'], "Ranchi Test")
    if report1:
        muni = report1.get('assigned_municipality')
        if muni == 'ranchi_mc':
            logger.info(f"✅ Auto-Assignment (Ranchi): SUCCESS (Assigned to {muni})")
        else:
            logger.error(f"❌ Auto-Assignment (Ranchi): FAILED (Assigned to {muni}, expected ranchi_mc)")
    
    # 2. Test London
    logger.info(f"Creating report in London {FAR_AWAY_COORDS}...")
    report2 = await create_report(token, FAR_AWAY_COORDS['lat'], FAR_AWAY_COORDS['lng'], "London Test")
    if report2:
        muni = report2.get('assigned_municipality')
        if muni is None:
             logger.info(f"✅ Auto-Assignment (London): SUCCESS (Assigned to None)")
        else:
             logger.warning(f"⚠️  Auto-Assignment (London): Unexpected assignment to {muni}")

async def main():
    print("=== STARTING VERIFICATION ===")
    
    # 1. Verify Admin Access
    token = await get_token(ADMIN_USER, ADMIN_PASS)
    if not token:
        logger.error("❌ Could not login as municipality admin. Check credentials.")
        return
        
    if await verify_dashboard(token):
        # 2. Verify Logic
        await verify_auto_assignment()
        
    print("=== VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(main())
