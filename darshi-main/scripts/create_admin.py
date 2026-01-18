"""
Script to create admin users in the Firestore admins collection.

Usage:
    python scripts/create_admin.py

This script will prompt for admin email and password, then create
the admin account in Firestore.
"""

import sys
import os
from getpass import getpass

# Add parent directory to path to import app modules
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)

# Change to parent directory so .env file can be found
os.chdir(parent_dir)

from app.services import admin_service

def main():
    print("=" * 60)
    print("Darshi Admin User Creation")
    print("=" * 60)
    print()

    # Get admin details
    email = input("Enter admin email: ").strip()
    password = getpass("Enter admin password: ")
    password_confirm = getpass("Confirm password: ")

    if password != password_confirm:
        print("ERROR: Passwords do not match!")
        return 1

    # Choose role
    print("\nSelect admin role:")
    print("1. super_admin (full access, can manage other admins)")
    print("2. moderator (can manage reports only)")
    role_choice = input("Enter choice (1 or 2): ").strip()

    if role_choice == "1":
        role = "super_admin"
    elif role_choice == "2":
        role = "moderator"
    else:
        print("ERROR: Invalid role choice!")
        return 1

    # Confirm
    print(f"\nCreating admin account:")
    print(f"  Email: {email}")
    print(f"  Role: {role}")
    confirm = input("\nProceed? (yes/no): ").strip().lower()

    if confirm != "yes":
        print("Cancelled.")
        return 0

    try:
        # Create admin
        admin = admin_service.create_admin(
            email=email,
            password=password,
            role=role,
            created_by="setup_script"
        )

        print("\n✓ Admin account created successfully!")
        print(f"  Email: {admin['email']}")
        print(f"  Role: {admin['role']}")
        print()
        print("The admin can now log in at /admin endpoint.")

        return 0

    except Exception as e:
        print(f"\n✗ ERROR: Failed to create admin account")
        print(f"  {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
