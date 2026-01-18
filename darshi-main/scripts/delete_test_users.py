#!/usr/bin/env python3
"""
Delete test users created for security auditing.

This script removes the test users created by create_test_users.py.

Usage:
    python3 scripts/delete_test_users.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services import db_service
from app.core.logging_config import setup_logging, get_logger

# Setup logging
setup_logging(log_level="INFO")
logger = get_logger(__name__)

def delete_test_users():
    """Delete all test users."""

    test_usernames = [
        "testuser1",
        "testuser2",
        "testuser3",
        "testuser4",
        "testadmin",
        # Old OAuth users from first attempt
        "testuser1_citizen",
        "testuser2_oauth",
        "testuser3_phone",
        "testuser4_github",
        "testadmin_audit"
    ]

    deleted_count = 0

    logger.info("=" * 70)
    logger.info("Deleting test users...")
    logger.info("=" * 70)

    for username in test_usernames:
        try:
            user = db_service.get_user_by_username(username)

            if user:
                # Delete user directly from Firestore
                user_id = user.get('id') or username
                db_service.db.collection('users').document(user_id).delete()
                deleted_count += 1
                logger.info(f"✅ Deleted user: {username}")
            else:
                logger.debug(f"User not found: {username}")

        except Exception as e:
            logger.error(f"❌ Error deleting user {username}: {e}", exc_info=True)

    logger.info("=" * 70)
    logger.info(f"Successfully deleted {deleted_count} test users")
    logger.info("=" * 70)

    return deleted_count

def main():
    """Main function."""
    try:
        # Ask for confirmation
        print("\n⚠️  WARNING: This will delete all test users created for security auditing.")
        print("Test users to be deleted:")
        print("  - testuser1")
        print("  - testuser2")
        print("  - testuser3")
        print("  - testuser4")
        print("  - testadmin")
        print("  (and any old test users from previous runs)")
        print()

        confirmation = input("Are you sure you want to delete these users? (yes/no): ").strip().lower()

        if confirmation not in ['yes', 'y']:
            logger.info("Operation cancelled by user.")
            return 0

        logger.info("Starting test user deletion script...")

        deleted_count = delete_test_users()

        if deleted_count > 0:
            logger.info("✅ Test user deletion completed successfully!")

            # Optionally delete credentials file
            if os.path.exists("test_users_credentials.txt"):
                delete_file = input("\nDelete test_users_credentials.txt file? (yes/no): ").strip().lower()
                if delete_file in ['yes', 'y']:
                    os.remove("test_users_credentials.txt")
                    logger.info("📄 Deleted credentials file: test_users_credentials.txt")
        else:
            logger.warning("No test users were deleted.")

        return 0

    except Exception as e:
        logger.error(f"Script failed: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit(main())
