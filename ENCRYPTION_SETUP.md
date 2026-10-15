# Database Encryption Setup Guide

## Overview

Your ERP project now includes **AES-256 file-level encryption** for the SQLite database using the `cryptography` library (Fernet).

**What this means:**
- `erp.db` becomes encrypted with AES-256
- Requires a master password to decrypt on startup
- No code changes needed in your app logic
- All existing DB queries work unchanged

---

## Quick Start

### 1. Encrypt Your Database (One-Time Setup)

Run the encryption utility:

```bash
python -m db.encrypt_db_utility
```

This will:
- Prompt for a master password (must be 12+ characters)
- Create a backup at `erp.db.backup_before_encrypt`
- Encrypt your database
- Display an encryption key you must save securely

### 2. Store Your Credentials

You'll need to save:
- **Master password** (what you typed)
- **Encryption key** ( displayed after encryption )

Keep these in a password manager. If you lose them, you **cannot** access your data.

### 3. Update Your Login Flow (Optional)

The current implementation includes basic encryption check in `main.py`.

For a production app, you'd want to:
1. Show a password dialog on startup if database is encrypted
2. Store the encryption key securely (not in plaintext)
3. Handle password change scenario

---

## How It Works

```
User enters master password
       ↓
PBKDF2-HMAC-SHA256 (100k iterations)
       ↓
Derive 32-byte key + salt
       ↓
Fernet AES-256 decryption
       ↓
Replace encrypted.db with erp.db
       ↓
App continues normally
```

**Encryption Details:**
- Algorithm: AES-256 (via Fernet)
- Key derivation: PBKDF2-HMAC-SHA256
- Iterations: 100,000
- Salt: Random 16 bytes per encryption
- Metadata stored in `erp.db.meta`

---

## Files Created/Modified

### New Files:
- `db/encryption.py` - Encryption/decryption logic
- `db/encrypt_db_utility.py` - Migration script
- `erp.db.meta` - Encryption metadata (created after encryption)

### Modified Files:
- `db/connection.py` - Added encryption check before DB access
- `main.py` - Added encryption check on startup

---

## Security Features

✅ **Password-based key derivation** (not stored)  
✅ **Random salt per encryption**  
✅ **100k iterations** (slows brute-force)  
✅ **Fernet authenticated encryption** (detects tampering)  
✅ **Database backup before encryption**  
✅ **No hardcoded keys**

---

## Limitations

⚠️ Single-user only (same as before)  
⚠️ No multi-device sync  
⚠️ Password must be entered manually (no auto-unlock)  
⚠️ If password lost → data permanently inaccessible

---

## Recovery Options

### If you forget password:
- **No recovery possible** - that's the point of encryption
- You must delete `erp.db` and `erp.db.meta` to start fresh
- Restore from backup if available

### If you need to change password:
1. Decrypt with old password
2. Re-encrypt with new password
3. Update stored credentials

---

## Testing

To verify encryption is working:

```python
from db.connection import ensure_database_decrypted
from db import encryption as enc

# Check if encrypted
print(enc.is_encrypted())  # True if .meta file exists

# Decrypt
key = "your-encrypted-key-here"
print(decrypt_database(key))  # True on success
```

---

## Next Steps

For production deployment, consider:

1. **GUI Password Dialog** - Show password prompt on startup
2. **Key Storage** - Use OS keychain (Windows Credential Manager)
3. **Password Policy** - Enforce complexity in login screen
4. **Backup Strategy** - Automated encrypted backups
5. **Key Rotation** - Periodic password/key changes

---

**WARNING:** This is a one-way encryption. Keep your password and key safe!
