import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime

from paths import DB_PATH
from .encryption import decrypt_database, encrypt_database, PasswordManager, load_encryption_params

DB_NAME = DB_PATH  # kept for old imports


def validate_progress(value):
    if value is None:
        return
    if isinstance(value, bool):
        raise ValueError("Progress must be a number.")
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise ValueError("Progress must be a number.")
    if v < 0 or v > 100:
        raise ValueError("Progress must be between 0 and 100.")


def validate_date(value, field_name="Date"):
    if value is None or value == "":
        return
    try:
        datetime.strptime(str(value)[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        raise ValueError(f"{field_name} must be a valid date (YYYY-MM-DD).")


def get_connection():
    connection = sqlite3.connect(DB_PATH, timeout=30.0)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")
    return connection


# Global password manager for the session
# This will be used when GUI password dialog is added
_password_manager = None


def set_database_password(password: str) -> bool:
    """Set the master password for database encryption/decryption."""
    global _password_manager
    from .encryption import PasswordManager
    _password_manager = PasswordManager()
    _password_manager.set_password(password)
    return True


def get_database_key() -> str:
    """Get the encryption key for current session."""
    if not _password_manager:
        raise RuntimeError("Database password not set")
    return _password_manager.get_key()


def ensure_database_decrypted() -> bool:
    """
    Ensure the database is decrypted and ready to use.
    Returns True on success, False on failure.
    """
    encrypted_meta = DB_PATH + '.meta'
    if not os.path.exists(encrypted_meta):
        return True  # Not encrypted, nothing to do
    
    # For encrypted databases, password must be set before calling this
    if not _password_manager:
        # Try to use encryption module directly
        from db import encryption as enc
        params = enc.load_encryption_params()
        if not params:
            return False
        return decrypt_database(enc.getpass.getpass("Database encryption password: "))
    
    # Try to decrypt using the cached password
    try:
        key = get_database_key()
        return decrypt_database(key)
    except Exception:
        return False


@contextmanager
def connect():
    """
    with connect() as connection:
        ...

    Commits on success, rolls back on error and ALWAYS closes.
    
    This wrapper automatically handles database decryption if needed.
    """

    if not ensure_database_decrypted():
        raise RuntimeError("Failed to decrypt database")

    connection = get_connection()

    try:
        yield connection
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# ==========================================================
# Encryption management functions
# ==========================================================

def enable_encryption(password: str) -> str:
    """
    Encrypt the database with the given password.
    Returns the encryption key that must be stored securely.
    """
    from .encryption import store_master_password_hash, save_encryption_params
    
    key_b64 = encrypt_database(password)
    encryption_params = store_master_password_hash(password)
    save_encryption_params(encryption_params)
    
    return key_b64


def disable_encryption(password: str) -> bool:
    """
    Decrypt the database using the master password.
    Returns True on success.
    """
    set_database_password(password)
    try:
        key = get_database_key()
        return decrypt_database(key)
    except Exception:
        return False

