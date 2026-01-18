#!/usr/bin/env python3
"""
Seed districts table from LGD (Local Government Directory) data.
Works inside Docker container using DATABASE_URL environment variable.
"""

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse
import psycopg2
from psycopg2.extras import execute_values


def get_db_connection():
    """Get database connection from DATABASE_URL or individual env vars"""
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        # Parse DATABASE_URL
        parsed = urlparse(database_url)
        return psycopg2.connect(
            host=parsed.hostname or 'postgres',
            port=parsed.port or 5432,
            database=parsed.path.lstrip('/') or 'darshi',
            user=parsed.username or 'darshi_app',
            password=parsed.password or ''
        )
    else:
        # Fall back to individual env vars
        return psycopg2.connect(
            host=os.environ.get('POSTGRES_HOST', 'postgres'),
            port=int(os.environ.get('POSTGRES_PORT', 5432)),
            database=os.environ.get('POSTGRES_DB', 'darshi'),
            user=os.environ.get('POSTGRES_USER', 'darshi_app'),
            password=os.environ.get('POSTGRES_PASSWORD', '')
        )


def seed_districts():
    """Load districts from LGD JSON and insert into database"""
    
    # Load LGD data
    lgd_file = Path(__file__).parent.parent / "lgd-districts.json"
    
    if not lgd_file.exists():
        print(f"❌ Error: {lgd_file} not found")
        return False
    
    print(f"📂 Loading districts from {lgd_file}")
    
    with open(lgd_file) as f:
        data = json.load(f)
    
    records = data.get('records', [])
    print(f"📊 Found {len(records)} districts in LGD data")
    
    # Connect to database
    try:
        print(f"🔌 Connecting to database...")
        conn = get_db_connection()
        cur = conn.cursor()
        print(f"✅ Connected!")
        
        # Check if districts table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'districts'
            )
        """)
        if not cur.fetchone()[0]:
            print("❌ Error: districts table does not exist. Run migration 15_districts.sql first.")
            return False
        
        # Check current count
        cur.execute("SELECT COUNT(*) FROM districts")
        current_count = cur.fetchone()[0]
        print(f"📊 Current district count: {current_count}")
        
        # Prepare data for bulk insert
        values = []
        for record in records:
            values.append((
                record['district_code'],
                record['district_name_english'],
                record.get('district_name_local', ''),
                record['state_code'],
                record['state_name_english'],
                record.get('district_census2011_code', '')
            ))
        
        # Bulk insert with ON CONFLICT
        execute_values(
            cur,
            """
            INSERT INTO districts (
                district_code, 
                district_name, 
                district_name_local,
                state_code, 
                state_name, 
                census_code
            )
            VALUES %s
            ON CONFLICT (district_code) DO NOTHING
            """,
            values
        )
        
        inserted = cur.rowcount
        conn.commit()
        
        print(f"\n✅ Seeding complete!")
        print(f"   Inserted: {inserted}")
        print(f"   Total in DB: {current_count + inserted}")
        
        cur.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = seed_districts()
    sys.exit(0 if success else 1)
