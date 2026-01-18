"""
Quick script to check a user's role and municipality_id in the database
Usage: python3 -m scripts.check_user_role <username>
"""
import sys
import asyncio
from app.services import postgres_service as db

async def check_user(username):
    try:
        user = await db.get_user_by_username(username)
        if not user:
            print(f"❌ User '{username}' not found")
            return
        
        print(f"✅ User found: {username}")
        print(f"   Email: {user.get('email')}")
        print(f"   Role: {user.get('role')}")
        print(f"   Municipality ID: {user.get('municipality_id')}")
        print(f"   Is Active: {user.get('is_active')}")
        print(f"   Is Verified: {user.get('is_verified')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 -m scripts.check_user_role <username>")
        sys.exit(1)
    
    username = sys.argv[1]
    asyncio.run(check_user(username))
