"""
Database encryption module using AES-256 (file-level encryption).
Uses Fernet symmetric encryption to protect erp.db at rest.
"""

import os
import base64
import json
import hashlib
import getpass
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

from paths import DB_PATH, SETTINGS_FILE, DATA_DIR


# ==========================================================
# Password Key Derivation
# ==========================================================

def derive_key(password: str, salt: bytes) -> bytes:
    """
    Derive a 32-byte key from password using PBKDF2HMAC-SHA256.
    Same approach as password hashing in security.py.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
        backend=default_backend()
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode('utf-8')))


def get_salt() -> bytes:
    """Generate a random salt for key derivation."""
    return os.urandom(16)


# ==========================================================
# Master Password Storage
# ==========================================================

def store_master_password_hash(password: str) -> dict:
    """
    Store a hash of the master password for verification.
    Returns encryption params (salt, hash) to save in settings.
    """
    salt = get_salt()
    key = derive_key(password, salt)
    # Store hash of the derived key (not the key itself!)
    password_hash = hashlib.sha256(key).hexdigest()
    return {
        'salt': base64.b64encode(salt).decode(),
        'hash': password_hash,
        'iterations': 100_000
    }


def verify_master_password(password: str, params: dict) -> bool:
    """Verify that a password matches the stored hash."""
    try:
        salt = base64.b64decode(params['salt'])
        key = derive_key(password, salt)
        return hashlib.sha256(key).hexdigest() == params['hash']
    except Exception:
        return False


# ==========================================================
# Encryption/Decryption
# ==========================================================

def encrypt_database(password: str, db_path: str = None) -> bytes:
    """
    Encrypt the database file in place.
    Returns Fernet key (must be stored securely).
    """
    if db_path is None:
        db_path = DB_PATH
    
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}")
    
    # Read plain database
    with open(db_path, 'rb') as f:
        plain_data = f.read()
    
    # Generate encryption key from password
    salt = get_salt()
    key = derive_key(password, salt)
    fernet = Fernet(key)
    
    # Encrypt
    encrypted_data = fernet.encrypt(plain_data)
    
    # Write encrypted database
    encrypted_path = db_path + '.encrypted'
    with open(encrypted_path, 'wb') as f:
        f.write(encrypted_data)
    
    # Write encryption metadata (salt + iterations, NOT the key)
    metadata = {
        'version': '1.0',
        'salt': base64.b64encode(salt).decode(),
        'iterations': 100_000,
        'original_size': len(plain_data)
    }
    
    metadata_path = db_path + '.meta'
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    # Replace original with encrypted
    os.replace(encrypted_path, db_path)
    
    # Return Fernet key (must be stored in encrypted_settings.json)
    return base64.b64encode(key).decode()


def decrypt_database(key_b64: str, db_path: str = None) -> bool:
    """
    Decrypt the database file using the provided Fernet key.
    Returns True on success, False on failure.
    """
    if db_path is None:
        db_path = DB_PATH
    
    encrypted_path = db_path
    decrypted_path = db_path + '.decrypted'
    
    try:
        # Read encryption metadata
        metadata_path = db_path + '.meta'
        if not os.path.exists(metadata_path):
            return False
        
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        # Read encrypted database
        if not os.path.exists(encrypted_path):
            return False
        
        with open(encrypted_path, 'rb') as f:
            encrypted_data = f.read()
        
        # Decrypt
        key = base64.b64decode(key_b64)
        fernet = Fernet(key)
        plain_data = fernet.decrypt(encrypted_data)
        
        # Write decrypted database
        with open(decrypted_path, 'wb') as f:
            f.write(plain_data)
        
        # Replace encrypted with decrypted (in place)
        os.replace(decrypted_path, db_path)
        
        return True
        
    except (InvalidToken, KeyError, json.JSONDecodeError):
        # Wrong key or corrupted data
        if os.path.exists(decrypted_path):
            os.remove(decrypted_path)
        return False


def delete_encryption_metadata(db_path: str = None):
    """Remove encryption-related files (for re-encryption)."""
    if db_path is None:
        db_path = DB_PATH
    
    for ext in ['.encrypted', '.meta', '.decrypted']:
        path = db_path + ext
        if os.path.exists(path):
            os.remove(path)


# ==========================================================
# Integration with Settings
# ==========================================================

def load_encryption_params():
    """Load encryption parameters from settings."""
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        return settings.get('encryption', {})
    except Exception:
        return {}


def save_encryption_params(params: dict):
    """Save encryption parameters to settings."""
    from config import load_settings, save_setting
    
    settings = load_settings()
    settings['encryption'] = params
    
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)


# ==========================================================
# Password prompts (GUI integration needed)
# ==========================================================

class PasswordManager:
    """Manages master password for database encryption."""
    
    def __init__(self):
        self._cached_key = None
        self._password = None
    
    def is_encrypted(self) -> bool:
        """Check if database is encrypted."""
        meta_path = DB_PATH + '.meta'
        return os.path.exists(meta_path)
    
    def set_password(self, password: str) -> bool:
        """Set the password (for decryption)."""
        self._password = password
        # Don't cache key - derive on demand
        return True
    
    def get_key(self) -> str:
        """Get the Fernet key by deriving it from password."""
        if self._cached_key:
            return self._cached_key
        
        params = load_encryption_params()
        if not params:
            raise ValueError("No encryption parameters found")
        
        salt = base64.b64decode(params['salt'])
        key = derive_key(self._password, salt)
        self._cached_key = base64.b64encode(key).decode()
        return self._cached_key
    
    def clear_cache(self):
        """Clear cached credentials."""
        self._cached_key = None
        self._password = None
