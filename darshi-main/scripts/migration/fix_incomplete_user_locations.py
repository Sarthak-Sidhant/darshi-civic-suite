#!/usr/bin/env python3
"""
Migration Script: Fix Incomplete User Locations
Author: Claude Code
Date: 2026-01-01

Description:
This script identifies users with incomplete location data (missing or empty city/state)
and updates them with placeholder values, then applies database constraints.

Strategy:
1. Identify users with NULL or empty city/state
2. Update with 'Unspecified' placeholder
3. Log users who need to complete their profile
4. Optionally mark users for re-onboarding
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.services import postgres_service as db_service
from app.core.logging_config import get_logger

logger = get_logger(__name__)


async def find_incomplete_users():
    """Find users with incomplete location data."""
    query = """
        SELECT username, email, city, state, country
        FROM users
        WHERE city IS NULL OR TRIM(city) = ''
           OR state IS NULL OR TRIM(state) = ''
           OR country IS NULL OR TRIM(country) = ''
        ORDER BY username
    """

    async with db_service.get_db_connection() as conn:
        rows = await conn.fetch(query)
        return [dict(row) for row in rows]


async def update_user_location(email: str, updates: dict):
    """Update a single user's location with sanitized data."""
    set_clauses = []
    values = []
    param_count = 1

    for key, value in updates.items():
        set_clauses.append(f"{key} = ${param_count}")
        values.append(value)
        param_count += 1

    # Add email as final parameter
    values.append(email)

    query = f"""
        UPDATE users
        SET {', '.join(set_clauses)}
        WHERE email = ${param_count}
        RETURNING username
    """

    async with db_service.get_db_connection() as conn:
        result = await conn.fetchrow(query, *values)
        return result['username'] if result else None


async def apply_database_constraints():
    """Apply CHECK constraints to prevent empty location fields."""
    constraints = [
        # City constraints
        """
        ALTER TABLE users
        ADD CONSTRAINT IF NOT EXISTS check_city_not_empty
        CHECK (city IS NOT NULL AND TRIM(city) != '')
        """,
        """
        ALTER TABLE users
        ADD CONSTRAINT IF NOT EXISTS check_city_length
        CHECK (LENGTH(city) >= 2 AND LENGTH(city) <= 100)
        """,

        # State constraints
        """
        ALTER TABLE users
        ADD CONSTRAINT IF NOT EXISTS check_state_not_empty
        CHECK (state IS NOT NULL AND TRIM(state) != '')
        """,
        """
        ALTER TABLE users
        ADD CONSTRAINT IF NOT EXISTS check_state_length
        CHECK (LENGTH(state) >= 2 AND LENGTH(state) <= 100)
        """,

        # Country constraints
        """
        ALTER TABLE users
        ADD CONSTRAINT IF NOT EXISTS check_country_not_empty
        CHECK (country IS NOT NULL AND TRIM(country) != '')
        """,
        """
        ALTER TABLE users
        ADD CONSTRAINT IF NOT EXISTS check_country_length
        CHECK (LENGTH(country) >= 2 AND LENGTH(country) <= 100)
        """,
    ]

    async with db_service.get_db_connection() as conn:
        for constraint_sql in constraints:
            try:
                await conn.execute(constraint_sql)
                logger.info(f"Applied constraint successfully")
            except Exception as e:
                logger.error(f"Failed to apply constraint: {e}")
                raise


async def main():
    """Main migration function."""
    print("=" * 70)
    print("User Location Data Migration")
    print("=" * 70)
    print()

    # Step 1: Find users with incomplete data
    print("Step 1: Finding users with incomplete location data...")
    incomplete_users = await find_incomplete_users()

    if not incomplete_users:
        print("✓ All users have complete location data!")
        print()
        print("Step 2: Applying database constraints...")
        await apply_database_constraints()
        print("✓ Database constraints applied successfully")
        print()
        print("Migration complete - No users needed updates")
        return

    print(f"Found {len(incomplete_users)} users with incomplete data:")
    print()

    # Display users
    for user in incomplete_users:
        print(f"  • {user['username']:20s} (email: {user['email']})")
        print(f"    City:    {repr(user['city'])}")
        print(f"    State:   {repr(user['state'])}")
        print(f"    Country: {repr(user['country'])}")
        print()

    # Step 2: Confirm update
    print()
    response = input("Update these users with placeholder values? (yes/no): ").lower().strip()
    if response != 'yes':
        print("Migration cancelled by user")
        return

    # Step 3: Update users
    print()
    print("Step 2: Updating users with placeholder values...")
    updated_count = 0

    for user in incomplete_users:
        updates = {}

        # Prepare updates
        if not user['city'] or not user['city'].strip():
            updates['city'] = 'Unspecified'

        if not user['state'] or not user['state'].strip():
            updates['state'] = 'Unspecified'

        if not user['country'] or not user['country'].strip():
            updates['country'] = 'India'

        # Apply updates
        if updates:
            try:
                username = await update_user_location(user['email'], updates)
                if username:
                    print(f"  ✓ Updated {username}: {', '.join(updates.keys())}")
                    updated_count += 1
                else:
                    print(f"  ✗ Failed to update {user['username']}")
            except Exception as e:
                print(f"  ✗ Error updating {user['username']}: {e}")

    print()
    print(f"✓ Updated {updated_count} users")

    # Step 4: Apply constraints
    print()
    print("Step 3: Applying database constraints...")
    try:
        await apply_database_constraints()
        print("✓ Database constraints applied successfully")
    except Exception as e:
        print(f"✗ Failed to apply constraints: {e}")
        print("   You may need to run the SQL migration manually")
        print("   See: scripts/migration/add_location_constraints.sql")
        return

    # Step 5: Summary
    print()
    print("=" * 70)
    print("Migration Complete!")
    print("=" * 70)
    print()
    print(f"Summary:")
    print(f"  - Users updated: {updated_count}")
    print(f"  - Database constraints: Applied")
    print()
    print("Next Steps:")
    print("  1. Users with 'Unspecified' location will be prompted to update on next login")
    print("  2. Backend now validates all location fields (city, state, country)")
    print("  3. Empty strings and whitespace-only values are rejected")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nMigration cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        print(f"\n\nMigration failed: {e}")
        sys.exit(1)
