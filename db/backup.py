"""Safe SQLite backup and restore helpers.

Restore is deliberately explicit: validate the selected backup, create a
verified safety copy of the current database, then atomically replace it.
The UI should ask the user to close/restart the application after restore.
"""
import os
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

from paths import DB_PATH, BACKUP_DIR
from .connection import get_connection
from .permissions import require_session_permission


def _check_database(path):
    connection = sqlite3.connect(str(path))
    try:
        result = connection.execute("PRAGMA integrity_check").fetchone()
        if not result or result[0] != "ok":
            raise ValueError(f"SQLite integrity_check failed: {result!r}")
        fk_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
        if fk_errors:
            raise ValueError(f"Database contains foreign-key violations: {fk_errors[:5]!r}")
    finally:
        connection.close()


def create_backup(source_path=DB_PATH, backup_dir=BACKUP_DIR):
    source_path = Path(source_path)
    backup_dir = Path(backup_dir)
    if not source_path.is_file():
        raise FileNotFoundError(f"Database not found: {source_path}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
    destination = backup_dir / f"erp_{stamp}.db"
    src = sqlite3.connect(str(source_path))
    dst = sqlite3.connect(str(destination))
    try:
        src.backup(dst)
        dst.commit()
    except Exception:
        dst.close()
        src.close()
        destination.unlink(missing_ok=True)
        raise
    finally:
        try: dst.close()
        except Exception: pass
        try: src.close()
        except Exception: pass
    _check_database(destination)
    return str(destination)


def restore_database(backup_path, target_path=DB_PATH, backup_dir=BACKUP_DIR):
    """Restore a validated backup, retaining a verified pre-restore copy."""
    session = get_connection()
    try:
        require_session_permission(session, "backup.restore")
    finally:
        session.close()

    backup_path = Path(backup_path).resolve()
    target_path = Path(target_path).resolve()
    if not backup_path.is_file():
        raise FileNotFoundError(f"Backup not found: {backup_path}")
    if backup_path == target_path:
        raise ValueError("The selected backup is the active database file.")
    _check_database(backup_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    safety_copy = None
    if target_path.exists():
        safety_copy = create_backup(target_path, backup_dir)
    fd, temp_name = tempfile.mkstemp(prefix="erp_restore_", suffix=".db", dir=str(target_path.parent))
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        source = sqlite3.connect(str(backup_path))
        destination = sqlite3.connect(str(temp_path))
        try:
            source.backup(destination)
            destination.commit()
        finally:
            destination.close()
            source.close()
        _check_database(temp_path)
        os.replace(temp_path, target_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    return {"restored_from": str(backup_path), "safety_backup": safety_copy}
