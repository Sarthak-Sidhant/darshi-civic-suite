#!/usr/bin/env python3
"""
Migration script to:
1. Parse latitude/longitude from location string
2. Reverse geocode to get human-readable addresses
3. Update all existing reports
"""

import firebase_admin
from firebase_admin import credentials, firestore
from app.services import geo_service
import asyncio
import time
import os

# Initialize Firebase
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/home/sidhant/Desktop/darshi/service-account.json'

try:
    firebase_admin.get_app()
except ValueError:
    cred = credentials.Certificate('/home/sidhant/Desktop/darshi/service-account.json')
    firebase_admin.initialize_app(cred)

db = firestore.client()

async def migrate_report_locations():
    """Migrate all reports to add lat/lng and human-readable addresses."""

    print("Fetching all reports...")
    reports = db.collection('reports').stream()

    updated_count = 0
    skipped_count = 0
    error_count = 0

    for doc in reports:
        report_id = doc.id
        data = doc.to_dict()
        location = data.get('location', '')

        # Skip if already has latitude and longitude
        if 'latitude' in data and 'longitude' in data:
            print(f"✓ {report_id}: Already migrated")
            skipped_count += 1
            continue

        # Parse coordinates from location string
        try:
            parts = location.split(',')
            if len(parts) != 2:
                print(f"✗ {report_id}: Invalid location format: {location}")
                error_count += 1
                continue

            lat = float(parts[0].strip())
            lng = float(parts[1].strip())

            # Reverse geocode to get address
            address = None
            try:
                address = await geo_service.reverse_geocode(lat, lng)
                if not address:
                    address = location  # Fallback to coordinates
                await asyncio.sleep(1)  # Rate limit for Nominatim (1 req/sec)
            except Exception as e:
                print(f"⚠ {report_id}: Reverse geocoding failed: {e}")
                address = location  # Fallback to coordinates

            # Update report
            update_data = {
                'latitude': lat,
                'longitude': lng,
                'location': address
            }

            db.collection('reports').document(report_id).update(update_data)
            print(f"✓ {report_id}: Updated - {address[:60]}...")
            updated_count += 1

        except Exception as e:
            print(f"✗ {report_id}: Migration failed: {e}")
            error_count += 1

    print(f"\nMigration complete!")
    print(f"  Updated: {updated_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Errors: {error_count}")

if __name__ == '__main__':
    asyncio.run(migrate_report_locations())
