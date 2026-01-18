import asyncio
import asyncpg
import os
import sys

# Add app directory to path
sys.path.append(os.getcwd())

# Load .env manually
try:
    with open('.env') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                # Handle potential quoting
                value = value.strip()
                if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                os.environ[key.strip()] = value
except Exception as e:
    print(f"Warning: Could not load .env: {e}")

from app.services.postgres_service import get_db_connection

async def apply_migration(filename):
    print(f"Applying {filename}...")
    with open(filename, 'r') as f:
        sql = f.read()
    
    async with get_db_connection() as conn:
        await conn.execute(sql)
    print("Done.")

if __name__ == "__main__":
    asyncio.run(apply_migration('migrations/07_report_updates.sql'))
