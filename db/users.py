"""User account operations that must be enforced outside the UI."""
import sqlite3

from .connection import connect
from security import hash_password, is_hashed, verify_password


def create_first_admin(full_name, username, password):
    """Atomically create the first Manager account on an empty database."""
    full_name = str(full_name or "").strip()
    username = str(username or "").strip()
    password = str(password or "")

    if not full_name:
        raise ValueError("Administrator full name is required.")
    if len(username) < 3 or any(char.isspace() for char in username):
        raise ValueError("Username must be at least 3 characters and contain no spaces.")
    if len(password) < 12:
        raise ValueError("Administrator password must contain at least 12 characters.")

    try:
        with connect() as connection:
            if connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] != 0:
                raise RuntimeError("An administrator already exists. Restart and sign in.")

            role = connection.execute(
                "SELECT id FROM roles WHERE name = 'Manager' COLLATE NOCASE"
            ).fetchone()
            if role is None:
                from .permissions import seed_roles
                seed_roles(connection)

            connection.execute(
                "INSERT INTO users(full_name, username, password, role, status) "
                "VALUES (?, ?, ?, 'Manager', 'Active')",
                (full_name, username, hash_password(password)),
            )
    except sqlite3.IntegrityError as error:
        if "username" in str(error).lower():
            raise ValueError("That username is already in use.") from error
        raise

    return True


def upgrade_legacy_password(user_id, password, stored_value):
    """Replace a legacy plain-text password with a scrypt hash.

    Call only AFTER a successful login.  Returns True when the row was
    upgraded.  It is a compare-and-swap on the exact value that was verified,
    so a password changed in the meantime is never overwritten.
    """
    if is_hashed(stored_value) or not verify_password(password, stored_value):
        return False

    with connect() as connection:
        cursor = connection.execute(
            "UPDATE users SET password = ? WHERE id = ? AND password = ?",
            (hash_password(password), user_id, stored_value),
        )
        return cursor.rowcount == 1
