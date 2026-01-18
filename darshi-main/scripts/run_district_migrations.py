#!/usr/bin/env python3
"""
Run district migrations and seed data.
Works inside Docker container using DATABASE_URL environment variable.

Usage:
    python scripts/run_district_migrations.py

This script:
1. Creates districts table (migration 15)
2. Adds district_code to broadcast_alerts (migration 16)
3. Seeds districts from LGD data (785 districts)
4. Backfills district_code in existing alerts
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlparse
import psycopg2


def get_db_connection():
    """Get database connection from DATABASE_URL or individual env vars"""
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        parsed = urlparse(database_url)
        return psycopg2.connect(
            host=parsed.hostname or 'postgres',
            port=parsed.port or 5432,
            database=parsed.path.lstrip('/') or 'darshi',
            user=parsed.username or 'darshi_app',
            password=parsed.password or ''
        )
    else:
        return psycopg2.connect(
            host=os.environ.get('POSTGRES_HOST', 'postgres'),
            port=int(os.environ.get('POSTGRES_PORT', 5432)),
            database=os.environ.get('POSTGRES_DB', 'darshi'),
            user=os.environ.get('POSTGRES_USER', 'darshi_app'),
            password=os.environ.get('POSTGRES_PASSWORD', '')
        )


def run_sql_file(cur, filepath: Path):
    """Run a SQL file"""
    print(f"  Running {filepath.name}...")
    with open(filepath) as f:
        sql = f.read()
    try:
        cur.execute(sql)
        print(f"  ✅ {filepath.name} completed")
        return True
    except Exception as e:
        print(f"  ⚠️ {filepath.name}: {e}")
        return False


def main():
    print("=" * 50)
    print("District Migration - Complete Setup (Python)")
    print("=" * 50)
    
    project_root = Path(__file__).parent.parent
    migrations_dir = project_root / "migrations"
    
    try:
        print("\n🔌 Connecting to database...")
        conn = get_db_connection()
        conn.autocommit = True
        cur = conn.cursor()
        print("✅ Connected!\n")
        
        # Step 1: Run migration 15 (districts table)
        print("Step 1: Creating districts table...")
        print("-" * 40)
        run_sql_file(cur, migrations_dir / "15_districts.sql")
        
        # Step 2: Run migration 16 (alter broadcast_alerts)
        print("\nStep 2: Adding district_code to broadcast_alerts...")
        print("-" * 40)
        run_sql_file(cur, migrations_dir / "16_alter_alerts_for_districts.sql")
        
        # Step 3: Seed districts
        print("\nStep 3: Seeding districts from LGD data...")
        print("-" * 40)
        
        # Check current count
        cur.execute("SELECT COUNT(*) FROM districts")
        current_count = cur.fetchone()[0]
        
        if current_count > 700:
            print(f"  Districts already seeded ({current_count} records)")
        else:
            # Import and run seed
            import json
            lgd_file = project_root / "lgd-districts.json"
            
            if lgd_file.exists():
                with open(lgd_file) as f:
                    data = json.load(f)
                
                records = data.get('records', [])
                print(f"  Loading {len(records)} districts...")
                
                from psycopg2.extras import execute_values
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
                
                execute_values(
                    cur,
                    """
                    INSERT INTO districts (
                        district_code, district_name, district_name_local,
                        state_code, state_name, census_code
                    ) VALUES %s ON CONFLICT (district_code) DO NOTHING
                    """,
                    values
                )
                print(f"  ✅ Inserted {cur.rowcount} districts")
            else:
                print(f"  ⚠️ lgd-districts.json not found")
        
        # Step 4: Backfill district_code
        print("\nStep 4: Backfilling district_code in existing alerts...")
        print("-" * 40)
        
        # Check if district_code column exists
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'broadcast_alerts' 
                AND column_name = 'district_code'
            )
        """)
        if cur.fetchone()[0]:
            cur.execute("""
                UPDATE broadcast_alerts ba
                SET district_code = d.district_code
                FROM districts d
                WHERE ba.district_code IS NULL
                  AND LOWER(TRIM(ba.district)) = LOWER(TRIM(d.district_name))
                  AND LOWER(TRIM(ba.state)) = LOWER(TRIM(d.state_name))
            """)
            print(f"  ✅ Backfilled {cur.rowcount} alerts")
        else:
            print("  ⚠️ district_code column doesn't exist yet")
        
        # Summary
        print("\n" + "=" * 50)
        print("✅ Migration Complete!")
        print("=" * 50)
        
        cur.execute("SELECT COUNT(*) FROM districts")
        district_count = cur.fetchone()[0]
        print(f"\nDistricts in database: {district_count}")
        
        # Check alerts
        cur.execute("SELECT COUNT(*) FROM broadcast_alerts")
        total_alerts = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM broadcast_alerts WHERE district_code IS NOT NULL")
        filled_alerts = cur.fetchone()[0]
        
        print(f"Alerts with district_code: {filled_alerts} / {total_alerts}")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
