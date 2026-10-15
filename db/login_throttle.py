"""
Persistent login throttling.

The failed-attempt counter lives in the database (table ``login_attempts``),
so closing and re-opening the application - or opening a second window -
no longer resets it.  Policy is unchanged from the previous in-memory
version: MAX_ATTEMPTS failures lock the username for LOCKOUT_SECONDS.

Honest limit: this is still a desktop application working on a local file.
Someone who controls the machine can edit the file; a real brute-force
defence for multi-user deployments belongs in a central server.
"""

import time

from .connection import connect

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 60
_PURGE_AFTER_SECONDS = 24 * 60 * 60     # forget idle names so the table stays small


def _key(username):
    return str(username or "").strip().lower()


def seconds_locked(username, now=None):
    """Seconds still locked (0 when the name may try to log in)."""
    now = time.time() if now is None else now
    with connect() as connection:
        row = connection.execute(
            "SELECT locked_until FROM login_attempts WHERE username = ?",
            (_key(username),),
        ).fetchone()
    if not row:
        return 0
    return max(0, int(row[0] - now + 0.999))


def record_failure(username, now=None):
    """
    Register one failed login.
    Returns ``(attempts_left, locked_seconds)``; ``locked_seconds`` > 0 means
    this failure triggered a lock.
    """
    now = time.time() if now is None else now
    key = _key(username)

    with connect() as connection:
        connection.execute("BEGIN IMMEDIATE")        # no lost updates between windows

        connection.execute(
            "DELETE FROM login_attempts WHERE updated_at < ? AND locked_until < ?",
            (now - _PURGE_AFTER_SECONDS, now),
        )

        row = connection.execute(
            "SELECT failed_count, locked_until FROM login_attempts WHERE username = ?",
            (key,),
        ).fetchone()
        count = (row[0] if row else 0) + 1

        if count >= MAX_ATTEMPTS:
            count, locked_until = 0, now + LOCKOUT_SECONDS
        else:
            locked_until = row[1] if row else 0

        connection.execute(
            """INSERT INTO login_attempts(username, failed_count, locked_until, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(username) DO UPDATE SET
                   failed_count = excluded.failed_count,
                   locked_until = excluded.locked_until,
                   updated_at   = excluded.updated_at""",
            (key, count, locked_until, now),
        )

    if locked_until > now:
        return 0, LOCKOUT_SECONDS
    return MAX_ATTEMPTS - count, 0


def clear(username):
    """Forget failures after a successful login."""
    with connect() as connection:
        connection.execute(
            "DELETE FROM login_attempts WHERE username = ?", (_key(username),)
        )
