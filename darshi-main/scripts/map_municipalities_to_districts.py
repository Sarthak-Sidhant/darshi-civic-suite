#!/usr/bin/env python3
"""
Map municipalities to districts using geocoding.
Uses existing municipality GPS coordinates to determine district via Nominatim.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.postgres_service import get_db_pool
from app.services.location_service import location_service


async def map_municipalities():
    """Map each municipality to its district using geocoding"""
    
    pool = await get_db_pool()
    
    async with pool.acquire() as conn:
        # Get all municipalities with GPS coordinates
        municipalities = await conn.fetch("""
            SELECT id, name, latitude, longitude, state
            FROM municipalities
            WHERE latitude IS NOT NULL 
            AND longitude IS NOT NULL
            AND district_code IS NULL
            ORDER BY id
        """)
        
        print(f"📍 Found {len(municipalities)} municipalities to map")
        
        mapped = 0
        failed = 0
        
        for muni in municipalities:
            try:
                # Reverse geocode to get district
                location_data = await location_service.reverse_geocode(
                    muni['latitude'],
                    muni['longitude']
                )
                
                if not location_data:
                    print(f"⚠️  No location data for {muni['name']}")
                    failed += 1
                    continue
                
                district_name = location_data.get('district')
                state_name = location_data.get('state')
                
                if not district_name:
                    print(f"⚠️  No district found for {muni['name']}")
                    failed += 1
                    continue
                
                # Find district code from districts table
                district = await conn.fetchrow("""
                    SELECT district_code FROM districts
                    WHERE LOWER(district_name) = LOWER($1)
                    AND LOWER(state_name) = LOWER($2)
                """, district_name, state_name)
                
                if not district:
                    print(f"⚠️  District '{district_name}' not found in LGD data for {muni['name']}")
                    failed += 1
                    continue
                
                # Update municipality with district_code
                await conn.execute("""
                    UPDATE municipalities 
                    SET district_code = $1 
                    WHERE id = $2
                """, district['district_code'], muni['id'])
                
                mapped += 1
                print(f"✓ {muni['name']} → {district_name} District (code: {district['district_code']})")
                
                # Rate limit: 1 request per second for Nominatim
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"❌ Error mapping {muni['name']}: {e}")
                failed += 1
    
    await pool.close()
    
    print(f"\n✅ Mapping complete!")
    print(f"   Mapped: {mapped}")
    print(f"   Failed: {failed}")
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(map_municipalities())
    sys.exit(0 if success else 1)
