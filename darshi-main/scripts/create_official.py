"""
Create Municipality Official Script
Usage: python3 scripts/create_official.py <username> <email> <password> <municipality_id> <role>

Roles: municipality_admin, municipality_staff
"""
import sys
import asyncio
import argparse
from app.services.auth_service import get_password_hash
from app.services import postgres_service as db
# We need to initialize the app settings for DB connection
from app.core.config import settings

# Initialize logging if needed
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("create_official")

async def create_official(username, email, password, municipality_id, role):
    try:
        print(f"Checking for existing user {username}...")
        existing = await db.get_user_by_username(username)
        if existing:
            print(f"User {username} already exists.")
            return

        print(f"Creating user {username} for {municipality_id} as {role}...")
        
        # Verify municipality exists
        # We can't verify easily if we don't have the function exposed or if DB is empty
        # but we proceed assuming ID is correct.

        # Create user manually in DB to bypass citizen role lock
        async with db.get_db_connection() as conn:
            hashed_pwd = get_password_hash(password)
            
            # Using raw SQL to ensure we set the columns correctly
            # Assuming 'users' table has municipality_id and role columns
            query = """
                INSERT INTO users (
                    username, email, password_hash, role, municipality_id, is_active, is_verified, created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, true, true, NOW(), NOW()
                ) RETURNING username
            """
            await conn.execute(query, username, email, hashed_pwd, role, municipality_id)
            
        print(f"Successfully created official: {username}")
        
    except Exception as e:
        print(f"Error creating official: {e}")

def main():
    parser = argparse.ArgumentParser(description="Create Municipality Official")
    parser.add_argument("username", help="Username")
    parser.add_argument("email", help="Email address")
    parser.add_argument("password", help="Password")
    parser.add_argument("municipality_id", help="Municipality ID (e.g., ranchi_mc)")
    parser.add_argument("--role", default="municipality_admin", choices=["municipality_admin", "municipality_staff"], help="Role")

    args = parser.parse_args()

    asyncio.run(create_official(args.username, args.email, args.password, args.municipality_id, args.role))

if __name__ == "__main__":
    main()
