#!/usr/bin/env python3
"""Create an admin account for Text2trade.

Usage:
    python scripts/create_admin.py --email admin@yourdomain.com --password YourSecurePass1!

Only way to create admin accounts. No self-registration as admin.
"""

import os
import sys
import argparse
import uuid
from datetime import datetime, timezone

# Add parent directory to path so we can import backend modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from auth import hash_password, validate_password_strength


def main():
    parser = argparse.ArgumentParser(description="Create an admin account for Text2trade")
    parser.add_argument("--email", required=True, help="Admin email address")
    parser.add_argument("--password", required=True, help="Admin password (min 8 chars, 1 number, 1 special char)")
    args = parser.parse_args()

    email = args.email.lower().strip()
    password = args.password

    # Validate password using same logic as auth module
    try:
        validate_password_strength(password)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Connect to MongoDB using same config as the app
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME", "text2trade")
    if not mongo_url:
        print("Error: MONGO_URL not set in .env")
        sys.exit(1)

    client = MongoClient(mongo_url)
    db = client[db_name]
    users = db["users"]

    # Check if admin already exists
    existing = users.find_one({"email": email})
    if existing:
        if existing.get("role") == "admin":
            print(f"Admin account already exists: {email}")
            sys.exit(0)
        else:
            # Upgrade existing user to admin
            users.update_one({"email": email}, {"$set": {"role": "admin"}})
            print(f"Upgraded existing user to admin: {email}")
            sys.exit(0)

    # Create admin user using the SAME hash function as auth module
    user_doc = {
        "user_id": str(uuid.uuid4()),
        "email": email,
        "password_hash": hash_password(password),
        "role": "admin",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_active": True,
    }

    try:
        users.insert_one(user_doc)
        print(f"Admin account created: {email}")
    except DuplicateKeyError:
        print(f"Email already registered: {email}")
        sys.exit(1)


if __name__ == "__main__":
    main()
