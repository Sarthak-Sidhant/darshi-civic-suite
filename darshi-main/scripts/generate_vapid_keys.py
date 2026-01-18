#!/usr/bin/env python3
"""
Generate VAPID keys for browser push notifications.

Run this script once to generate keys, then add them to your .env file:
VAPID_PUBLIC_KEY=<public_key>
VAPID_PRIVATE_KEY=<private_key>
VAPID_ADMIN_EMAIL=admin@darshi.app
"""

from pywebpush import Vapid

def generate_vapid_keys():
    """Generate VAPID public and private keys."""
    vapid = Vapid()
    vapid.generate_keys()

    print("\n" + "="*60)
    print("VAPID Keys Generated Successfully!")
    print("="*60)
    print("\nAdd these to your .env file:\n")
    print(f"VAPID_PUBLIC_KEY={vapid.public_key.decode('utf-8')}")
    print(f"VAPID_PRIVATE_KEY={vapid.private_key.decode('utf-8')}")
    print(f"VAPID_ADMIN_EMAIL=admin@darshi.app")
    print("\nAlso add the public key to frontend/.env:")
    print(f"VITE_VAPID_PUBLIC_KEY={vapid.public_key.decode('utf-8')}")
    print("\n" + "="*60)
    print("IMPORTANT: Keep the private key secure! Never commit it to git.")
    print("="*60 + "\n")

if __name__ == "__main__":
    generate_vapid_keys()
