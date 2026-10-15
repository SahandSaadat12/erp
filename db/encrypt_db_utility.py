#!/usr/bin/env python
"""
Database Encryption Migration Utility

This script helps migrate an existing SQLite database to encrypted format.
Run this ONCE on your existing erp.db file.

Usage:
    python -m db.encrypt_db_utility

The utility will:
1. Prompt for a master password (must be 12+ characters)
2. Encrypt the database with that password
3. Store encryption params in settings.json
4. Keep the original database safe until encryption succeeds

WARNING: This is a one-way operation. Keep your master password safe!
If you lose it, you CANNOT access your database.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.connection import enable_encryption, get_connection
from paths import DB_PATH
import getpass


def main():
    print("=" * 60)
    print("DATABASE ENCRYPTION MIGRATION UTILITY")
    print("=" * 60)
    print()
    print("This will encrypt your erp.db file with a master password.")
    print()
    
    # Check if already encrypted
    if os.path.exists(DB_PATH + '.meta'):
        print("ERROR: Database is already encrypted!")
        print("Remove .meta file first if you want to re-encrypt.")
        return False
    
    # Get password
    print("STEP 1: Create a master password")
    print("  - Must be at least 12 characters")
    print("  - Store this password securely!")
    print("  - If lost, you CANNOT access your database")
    print()
    
    password = getpass.getpass("Enter master password: ")
    if len(password) < 12:
        print("ERROR: Password must be at least 12 characters")
        return False
    
    confirm = getpass.getpass("Confirm master password: ")
    if password != confirm:
        print("ERROR: Passwords do not match")
        return False
    
    print()
    print("STEP 2: Backing up database...")
    
    # Create backup
    backup_path = DB_PATH + '.backup_before_encrypt'
    with open(DB_PATH, 'rb') as src:
        with open(backup_path, 'wb') as dst:
            dst.write(src.read())
    
    print(f"  Backup created: {backup_path}")
    print()
    
    # Encrypt
    print("STEP 3: Encrypting database...")
    try:
        key = enable_encryption(password)
        print("  Encryption successful!")
        print()
        print("=" * 60)
        print("IMPORTANT: Save this encryption key securely!")
        print("=" * 60)
        print()
        print(f"ENCRYPTION KEY: {key}")
        print()
        print("Store this key in a secure location (password manager, etc.)")
        print("This key is required to decrypt the database on future runs.")
        print()
        print("=" * 60)
        print("MIGRATION COMPLETE")
        print("=" * 60)
        print()
        print("Next steps:")
        print("  1. The original erp.db is now encrypted")
        print("  2. The backup is at:", backup_path)
        print("  3. Store your encryption key and password safely")
        print("  4. When running the app, you'll need to decrypt first")
        print()
        
        return True
        
    except Exception as e:
        print(f"ERROR: Encryption failed: {e}")
        print()
        print("Restoring from backup...")
        try:
            os.remove(DB_PATH)
            os.rename(backup_path, DB_PATH)
            print("  Backup restored")
        except Exception as restore_err:
            print(f"  Warning: Could not restore backup: {restore_err}")
        
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
