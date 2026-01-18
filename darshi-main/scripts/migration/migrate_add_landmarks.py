#!/usr/bin/env python3
"""
Migration script to update existing reports with landmark-based addresses.
"""

import firebase_admin
from firebase_admin import credentials, firestore
import asyncio
import sys
import os

sys.path.insert(0, '/home/sidhant/Desktop/darshi')
from app.services import geo_service

# Initialize Firebase
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/home/sidhant/Desktop/darshi/service-account.json'

try:
    firebase_admin.get_app()
except ValueError:
    cred = credentials.Certificate('/home/sidhant/Desktop/darshi/service-account.json')
    firebase_admin.initialize_app(cred)

db = firestore.client()

async def migrate_report_landmarks():
    """Update all reports to add landmark-based addresses."""

    print("Fetching all reports...")
    reports = db.collection('reports').stream()

    updated_count = 0
    skipped_count = 0
    error_count = 0

    for doc in reports:
        report_id = doc.id
        data = doc.to_dict()

        # Check if report has latitude and longitude
        if 'latitude' not in data or 'longitude' not in data:
            print(f"⚠ {report_id}: No lat/lng, skipping")
            skipped_count += 1
            continue

        lat = data['latitude']
        lng = data['longitude']
        old_location = data.get('location', 'N/A')

        try:
            # Get new address with landmarks
            new_address = await geo_service.reverse_geocode(lat, lng)

            # Only update if address changed
            if new_address != old_location:
                db.collection('reports').document(report_id).update({
                    'location': new_address
                })
                print(f"✓ {report_id}:")
                print(f"  Old: {old_location}")
                print(f"  New: {new_address[:80]}...")
                print()
                updated_count += 1
            else:
                print(f"= {report_id}: No change")
                skipped_count += 1

            # Rate limit for Overpass API (1 request per 1.5 seconds)
            await asyncio.sleep(1.5)

        except Exception as e:
            print(f"✗ {report_id}: Migration failed: {e}")
            error_count += 1

    print(f"\n{'='*70}")
    print(f"Migration complete!")
    print(f"  Updated: {updated_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Errors: {error_count}")
    print(f"{'='*70}")

if __name__ == '__main__':
    asyncio.run(migrate_report_landmarks())
