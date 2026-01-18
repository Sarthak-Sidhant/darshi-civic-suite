#!/usr/bin/env python3
"""
Backfill reports with city, state, and district_code using Nominatim reverse geocoding.
Run inside the backend container.
"""

import os
import sys
import time
import asyncio
from urllib.parse import urlparse
import psycopg2
import httpx

def get_db_connection():
    """Get database connection from DATABASE_URL"""
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        parsed = urlparse(database_url)
        return psycopg2.connect(
            host=parsed.hostname or 'postgres',
            port=parsed.port or 5432,
            database=parsed.path.lstrip('/') or 'darshi',
            user=parsed.username or 'postgres',
            password=parsed.password or ''
        )
    return psycopg2.connect(
        host=os.environ.get('POSTGRES_HOST', 'postgres'),
        port=int(os.environ.get('POSTGRES_PORT', 5432)),
        database=os.environ.get('POSTGRES_DB', 'darshi'),
        user=os.environ.get('POSTGRES_USER', 'postgres'),
        password=os.environ.get('POSTGRES_PASSWORD', '')
    )


async def reverse_geocode(lat: float, lng: float) -> dict:
    """Call Nominatim to get city/state from coordinates"""
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": lat,
        "lon": lng,
        "format": "json",
        "zoom": 10,
        "addressdetails": 1,
    }
    headers = {"User-Agent": "Darshi-Backfill/1.0"}
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, headers=headers, timeout=30.0)
            if resp.status_code == 200:
                data = resp.json()
                address = data.get('address', {})
                
                # For India, state_district IS the district (like "Ranchi", "Mumbai")
                # county is sometimes used for subdivisions
                # city/town/village are smaller areas within districts
                district = (address.get('state_district') or
                           address.get('county') or
                           address.get('city') or
                           address.get('town') or
                           address.get('village') or
                           '')
                
                state = address.get('state', '')
                
                return {'city': district, 'state': state}
        except Exception as e:
            print(f"  Geocode error for {lat},{lng}: {e}")
    
    return {'city': '', 'state': ''}


async def main():
    print("=" * 50)
    print("Backfill Reports with Location Data")
    print("=" * 50)
    
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()
    
    # Get all reports with lat/lng but missing city/state
    cur.execute("""
        SELECT id, latitude, longitude, city, state 
        FROM reports 
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        ORDER BY created_at DESC
    """)
    reports = cur.fetchall()
    
    print(f"\nFound {len(reports)} reports with coordinates")
    
    # Load districts for matching
    cur.execute("SELECT district_code, district_name, state_name FROM districts")
    districts = {(row[1].lower(), row[2].lower()): row[0] for row in cur.fetchall()}
    print(f"Loaded {len(districts)} districts for matching")
    
    updated = 0
    matched = 0
    
    for i, (report_id, lat, lng, existing_city, existing_state) in enumerate(reports):
        print(f"\n[{i+1}/{len(reports)}] Report {report_id[:8]}...")
        
        # Skip if already has city/state
        if existing_city and existing_state:
            city, state = existing_city, existing_state
            print(f"  Already has: {city}, {state}")
        else:
            # Call Nominatim
            result = await reverse_geocode(lat, lng)
            city = result['city']
            state = result['state']
            
            if city or state:
                print(f"  Geocoded: {city}, {state}")
                cur.execute("""
                    UPDATE reports SET city = %s, state = %s WHERE id = %s
                """, (city, state, report_id))
                updated += 1
            else:
                print(f"  No location found for {lat}, {lng}")
            
            # Rate limit Nominatim (1 req/sec)
            await asyncio.sleep(1.1)
        
        # Try to match district_code
        if city and state:
            key = (city.lower(), state.lower())
            district_code = districts.get(key)
            
            if district_code:
                cur.execute("""
                    UPDATE reports SET district_code = %s WHERE id = %s
                """, (district_code, report_id))
                matched += 1
                print(f"  Matched district: {district_code}")
            else:
                # Try fuzzy match on city only
                for (d_name, d_state), d_code in districts.items():
                    if city.lower() in d_name or d_name in city.lower():
                        if state.lower() in d_state or d_state in state.lower():
                            cur.execute("""
                                UPDATE reports SET district_code = %s WHERE id = %s
                            """, (d_code, report_id))
                            matched += 1
                            print(f"  Fuzzy matched: {d_code} ({d_name})")
                            break
    
    print("\n" + "=" * 50)
    print(f"✅ Backfill complete!")
    print(f"   Geocoded: {updated}")
    print(f"   District matched: {matched}")
    print("=" * 50)
    
    cur.close()
    conn.close()


if __name__ == "__main__":
    asyncio.run(main())
