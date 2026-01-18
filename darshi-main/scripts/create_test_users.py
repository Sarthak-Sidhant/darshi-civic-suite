#!/usr/bin/env python3
"""
Create test users for security auditing.

This script creates test users with USERNAME/PASSWORD authentication
that can login through the regular /api/v1/auth/token endpoint.

Usage:
    python3 scripts/create_test_users.py

The script will output the credentials to a file: test_users_credentials.txt
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services import db_service, auth_service
from app.core.logging_config import setup_logging, get_logger

# Setup logging
setup_logging(log_level="INFO")
logger = get_logger(__name__)

def create_test_users():
    """Create 5 test users with USERNAME/PASSWORD authentication."""

    test_users = [
        {
            "username": "testuser1",
            "email": "testuser1@darshi.test",
            "password": "TestPass123!",
            "phone": None,
            "full_name": "Test User One",
            "role": "citizen",
            "description": "Regular citizen user #1"
        },
        {
            "username": "testuser2",
            "email": "testuser2@darshi.test",
            "password": "TestPass456!",
            "phone": "+919876543210",
            "full_name": "Test User Two",
            "role": "citizen",
            "description": "Regular citizen user #2 with phone"
        },
        {
            "username": "testuser3",
            "email": "testuser3@darshi.test",
            "password": "TestPass789!",
            "phone": None,
            "full_name": "Test User Three",
            "role": "citizen",
            "description": "Regular citizen user #3"
        },
        {
            "username": "testuser4",
            "email": "testuser4@darshi.test",
            "password": "TestPass000!",
            "phone": None,
            "full_name": "Test User Four",
            "role": "citizen",
            "description": "Regular citizen user #4"
        },
        {
            "username": "testadmin",
            "email": "testadmin@darshi.test",
            "password": "AdminPass123!",
            "phone": None,
            "full_name": "Test Admin User",
            "role": "admin",
            "description": "Admin user for testing admin endpoints"
        }
    ]

    created_users = []
    credentials = []

    logger.info("=" * 70)
    logger.info("Creating test users for security auditing...")
    logger.info("=" * 70)

    for user_data in test_users:
        username = user_data["username"]

        # Check if user already exists
        existing_user = db_service.get_user_by_username(username)
        if existing_user:
            logger.warning(f"User {username} already exists. Skipping...")
            continue

        # Prepare user data for database
        db_user_data = {
            "username": user_data["username"],
            "email": user_data.get("email"),
            "phone": user_data.get("phone"),
            "full_name": user_data["full_name"],
            "role": user_data["role"],
            "hashed_password": auth_service.get_password_hash(user_data["password"]),
            "oauth_provider": None,  # NOT OAuth users
            "oauth_id": None,
            "profile_picture": None,
            "email_verified": False,  # Not verified yet
            "phone_verified": False,
            "notification_enabled": True,
            "location_tracking_enabled": True,
            "public_profile": True,
            "reports_count": 0,
            "upvotes_received": 0,
            "lat": 19.0760,  # Mumbai coordinates for testing
            "lng": 72.8777,
            "location_address": "Mumbai, Maharashtra, India"
        }

        try:
            # Create user in database
            user_id = db_service.create_user(db_user_data)

            if user_id:
                created_users.append(username)
                logger.info(f"✅ Created user: {username} ({user_data['description']})")

                # Prepare credentials info
                cred_info = {
                    "username": username,
                    "email": user_data.get("email", "N/A"),
                    "password": user_data["password"],
                    "phone": user_data.get("phone", "N/A"),
                    "role": user_data["role"],
                    "description": user_data["description"]
                }
                credentials.append(cred_info)
            else:
                logger.error(f"❌ Failed to create user: {username}")

        except Exception as e:
            logger.error(f"❌ Error creating user {username}: {e}", exc_info=True)

    logger.info("=" * 70)
    logger.info(f"Successfully created {len(created_users)} test users")
    logger.info("=" * 70)

    return credentials

def save_credentials(credentials):
    """Save credentials to a file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    output = []
    output.append("=" * 80)
    output.append("DARSHI TEST USERS - SECURITY AUDIT CREDENTIALS")
    output.append("=" * 80)
    output.append(f"Generated: {timestamp}")
    output.append("")
    output.append("⚠️  IMPORTANT: These are test credentials for security auditing only.")
    output.append("    Delete these users after the audit is complete.")
    output.append("")
    output.append("All users use USERNAME/PASSWORD authentication.")
    output.append("Login via: POST /api/v1/auth/token")
    output.append("")
    output.append("=" * 80)
    output.append("")

    for i, cred in enumerate(credentials, 1):
        output.append(f"USER #{i}: {cred['username']}")
        output.append("-" * 80)
        output.append(f"Role:           {cred['role'].upper()}")
        output.append(f"Description:    {cred['description']}")
        output.append(f"Username:       {cred['username']}")
        output.append(f"Email:          {cred['email']}")
        output.append(f"Password:       {cred['password']}")
        output.append(f"Phone:          {cred['phone']}")
        output.append("")
        output.append("=" * 80)
        output.append("")

    # API testing section
    output.append("")
    output.append("🔧 QUICK LOGIN COMMANDS")
    output.append("=" * 80)
    output.append("")

    for i, cred in enumerate(credentials, 1):
        output.append(f"# Login as {cred['username']} ({cred['role']})")
        if cred['role'] == 'admin':
            output.append(f"curl -X POST http://localhost:8080/api/v1/admin/login \\")
            output.append(f"  -H 'Content-Type: application/json' \\")
            output.append(f"  -d '{{\"username\": \"{cred['username']}\", \"password\": \"{cred['password']}\"}}'")
        else:
            output.append(f"curl -X POST http://localhost:8080/api/v1/auth/token \\")
            output.append(f"  -H 'Content-Type: application/x-www-form-urlencoded' \\")
            output.append(f"  -d 'username={cred['username']}&password={cred['password']}'")
        output.append("")

    output.append("=" * 80)
    output.append("")

    # Web login section
    output.append("")
    output.append("🌐 WEB LOGIN")
    output.append("=" * 80)
    output.append("")
    output.append("1. Go to: https://darshi.app/signin")
    output.append("2. Enter username and password from above")
    output.append("3. Click 'Sign In'")
    output.append("")
    output.append("For local testing:")
    output.append("1. Go to: http://localhost:5173/signin")
    output.append("2. Enter username and password")
    output.append("")
    output.append("=" * 80)
    output.append("")

    # Security testing notes
    output.append("")
    output.append("🔒 SECURITY TESTING CHECKLIST")
    output.append("=" * 80)
    output.append("")
    output.append("[ ] Test authentication bypass attempts")
    output.append("[ ] Verify JWT token expiration (30 days for citizens, 1 hour for admins)")
    output.append("[ ] Test authorization checks (citizen vs admin endpoints)")
    output.append("[ ] Verify rate limiting (3/hr anonymous, 10/hr registered)")
    output.append("[ ] Test input validation and sanitization")
    output.append("[ ] Verify CORS and security headers")
    output.append("[ ] Test password strength requirements")
    output.append("[ ] Check for information disclosure in error messages")
    output.append("[ ] Test SQL injection (should be N/A with Firestore)")
    output.append("[ ] Test XSS attacks (input sanitization)")
    output.append("[ ] Test CSRF protection")
    output.append("[ ] Verify secure password hashing (bcrypt)")
    output.append("")
    output.append("=" * 80)
    output.append("")

    # Admin endpoints to test
    output.append("")
    output.append("🔐 ADMIN ENDPOINTS TO TEST (requires admin token)")
    output.append("=" * 80)
    output.append("")
    output.append("GET    /api/v1/admin/analytics/dashboard")
    output.append("GET    /api/v1/admin/analytics/audit-logs")
    output.append("PUT    /api/v1/admin/report/{report_id}/status")
    output.append("POST   /api/v1/admin/report/{report_id}/comment")
    output.append("GET    /api/v1/admin/reports")
    output.append("DELETE /api/v1/admin/report/{report_id}")
    output.append("POST   /api/v1/admin/create-admin")
    output.append("")
    output.append("Verify that regular users CANNOT access these endpoints!")
    output.append("")
    output.append("=" * 80)

    # Write to file
    output_file = "test_users_credentials.txt"
    with open(output_file, "w") as f:
        f.write("\n".join(output))

    logger.info(f"📄 Credentials saved to: {output_file}")

    # Also print to console
    print("\n" + "\n".join(output))

def main():
    """Main function."""
    try:
        logger.info("Starting test user creation script...")

        credentials = create_test_users()

        if credentials:
            save_credentials(credentials)
            logger.info("✅ Test user creation completed successfully!")
            logger.info("⚠️  Remember to delete these test users after the security audit.")
        else:
            logger.warning("No new users were created. They may already exist.")

        return 0

    except Exception as e:
        logger.error(f"Script failed: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit(main())
