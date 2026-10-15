"""Regression tests for the post-audit hardening (temporary databases only)."""
import sqlite3
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import paths
import db.connection as db_connection
from db.migrations import init_database
from security import hash_password, is_hashed, verify_password


class HardeningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.db_path = str(base / "erp.db")
        self.patches = [
            patch.object(paths, "DB_PATH", self.db_path),
            patch.object(paths, "BACKUP_DIR", str(base / "backups")),
            patch.object(db_connection, "DB_PATH", self.db_path),
        ]
        for p in self.patches:
            p.start()
        init_database()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.temp.cleanup()

    def _add_user(self, username, stored):
        con = sqlite3.connect(self.db_path)
        try:
            cur = con.execute(
                "INSERT INTO users(full_name, username, password, role, status) "
                "VALUES (?, ?, ?, 'QC', 'Active')", (username, username, stored))
            con.commit()
            return cur.lastrowid
        finally:
            con.close()

    def _stored(self, user_id):
        con = sqlite3.connect(self.db_path)
        try:
            return con.execute("SELECT password FROM users WHERE id=?", (user_id,)).fetchone()[0]
        finally:
            con.close()

    # ---- SEC-03: legacy plaintext passwords -------------------------------
    def test_legacy_plaintext_password_is_upgraded_to_hash(self):
        from db.users import upgrade_legacy_password
        uid = self._add_user("legacy", "plain-secret-1")
        self.assertTrue(upgrade_legacy_password(uid, "plain-secret-1", "plain-secret-1"))
        stored = self._stored(uid)
        self.assertTrue(is_hashed(stored))
        self.assertTrue(verify_password("plain-secret-1", stored))
        self.assertFalse(verify_password("wrong", stored))

    def test_upgrade_does_not_touch_hashed_or_wrong_password(self):
        from db.users import upgrade_legacy_password
        hashed = hash_password("already-hashed-1")
        uid = self._add_user("modern", hashed)
        self.assertFalse(upgrade_legacy_password(uid, "already-hashed-1", hashed))
        self.assertEqual(self._stored(uid), hashed)
        uid2 = self._add_user("legacy2", "plain-secret-2")
        self.assertFalse(upgrade_legacy_password(uid2, "not-the-password", "plain-secret-2"))
        self.assertEqual(self._stored(uid2), "plain-secret-2")

    def test_upgrade_is_compare_and_swap(self):
        """If the password changed meanwhile, the stale value must not overwrite it."""
        from db.users import upgrade_legacy_password
        uid = self._add_user("race", "plain-secret-3")
        changed = hash_password("changed-in-between")
        con = sqlite3.connect(self.db_path)
        con.execute("UPDATE users SET password=? WHERE id=?", (changed, uid)); con.commit(); con.close()
        self.assertFalse(upgrade_legacy_password(uid, "plain-secret-3", "plain-secret-3"))
        self.assertEqual(self._stored(uid), changed)

    # ---- DB-01: lock waiting ------------------------------------------------
    def test_connections_wait_for_locks_instead_of_failing_fast(self):
        con = db_connection.get_connection()
        try:
            self.assertGreaterEqual(con.execute("PRAGMA busy_timeout").fetchone()[0], 30000)
            self.assertEqual(con.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        finally:
            con.close()

    def test_second_writer_waits_for_first_writer(self):
        locked = threading.Event()
        errors = []

        def hold_write_lock():
            try:
                holder = sqlite3.connect(self.db_path, timeout=30)   # created in THIS thread
                holder.execute("BEGIN IMMEDIATE")
                locked.set()
                time.sleep(0.4)
                holder.commit()
                holder.close()
            except Exception as error:      # pragma: no cover - reported below
                errors.append(error)
                locked.set()

        t = threading.Thread(target=hold_write_lock)
        t.start()
        self.assertTrue(locked.wait(10))
        try:
            with db_connection.connect() as con:      # must wait for the holder, then succeed
                con.execute("INSERT INTO settings(setting_key, setting_value) VALUES ('t', '1')")
        finally:
            t.join()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
