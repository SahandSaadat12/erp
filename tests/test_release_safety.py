"""Regression tests for release-safety fixes; uses temporary SQLite databases only."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import paths
import db.connection as db_connection
from db.migrations import init_database
from db.expenses import _validated_amount, _validated_status, get_expense_total, get_project_actual_price, delete_expense
from db.backup import create_backup, restore_database
from db.users import create_first_admin
from db.history import set_session_user
from db.lookups import save_entity
from security import is_hashed, verify_password


class ReleaseSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.db_path = str(self.base / "erp.db")
        self.backup_dir = str(self.base / "backups")
        self.path_patch = patch.object(paths, "DB_PATH", self.db_path)
        self.backup_patch = patch.object(paths, "BACKUP_DIR", self.backup_dir)
        self.connection_patch = patch.object(db_connection, "DB_PATH", self.db_path)
        self.path_patch.start(); self.backup_patch.start(); self.connection_patch.start()
        init_database()

    def tearDown(self):
        self.connection_patch.stop(); self.backup_patch.stop(); self.path_patch.stop()
        self.temp.cleanup()

    def test_fresh_database_has_no_default_accounts(self):
        con = sqlite3.connect(self.db_path)
        try:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM users").fetchone()[0], 0)
            self.assertEqual(con.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        finally:
            con.close()

    def test_first_admin_is_created_with_hashed_password_and_only_once(self):
        create_first_admin("Test Admin", "testadmin", "a-long-test-password")
        con = sqlite3.connect(self.db_path)
        try:
            row = con.execute(
                "SELECT username, password, role, status FROM users"
            ).fetchone()
            self.assertEqual(row[0], "testadmin")
            self.assertTrue(is_hashed(row[1]))
            self.assertTrue(verify_password("a-long-test-password", row[1]))
            self.assertEqual(row[2:], ("Manager", "Active"))
        finally:
            con.close()
        with self.assertRaises(RuntimeError):
            create_first_admin("Second Admin", "secondadmin", "another-long-password")

    def test_amount_and_status_validation(self):
        self.assertEqual(_validated_amount("1,234.50"), 1234.5)
        for invalid in ("abc", -1, float("nan"), float("inf"), None, True):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    _validated_amount(invalid)
        with self.assertRaises(ValueError):
            _validated_status("Unknown")

    def test_cancelled_expenses_do_not_count(self):
        con = sqlite3.connect(self.db_path)
        con.execute("INSERT INTO projects(project_code, project_name, project_status) VALUES ('T-1','Test','Open')")
        project_id = con.execute("SELECT id FROM projects WHERE project_code='T-1'").fetchone()[0]
        con.executemany(
            "INSERT INTO expenses(project_id, title, amount, status) VALUES (?, ?, ?, ?)",
            [(project_id, "Paid", 20, "Paid"), (project_id, "Pending", 40, "Pending"),
             (project_id, "Cancelled", 900, "Cancelled")],
        )
        con.commit(); con.close()
        self.assertEqual(get_expense_total(), 60)
        self.assertEqual(get_project_actual_price(project_id), 60)

    def test_destructive_operation_requires_authenticated_permission(self):
        with self.assertRaises(PermissionError):
            delete_expense(1)

    def test_user_management_write_requires_users_manage(self):
        with self.assertRaises(PermissionError):
            save_entity("managers", None, {
                "full_name": "Injected", "username": "injected",
                "password": "a-long-password", "role": "Manager", "status": "Active"
            }, current_user={"permissions": {"settings.manage"}})

    def test_backup_restore_round_trip_and_safety_copy(self):
        con = sqlite3.connect(self.db_path)
        con.execute("INSERT INTO projects(project_code, project_name, project_status) VALUES ('T-2','Original','Open')")
        con.commit(); con.close()
        create_first_admin("Test Admin", "testadmin", "a-long-test-password")
        set_session_user(1, "testadmin")
        backup = create_backup(self.db_path, self.backup_dir)
        con = sqlite3.connect(self.db_path)
        con.execute("UPDATE projects SET project_name='Changed' WHERE project_code='T-2'")
        con.commit(); con.close()
        result = restore_database(backup, self.db_path, self.backup_dir)
        con = sqlite3.connect(self.db_path)
        try:
            self.assertEqual(con.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(con.execute("SELECT project_name FROM projects WHERE project_code='T-2'").fetchone()[0], "Original")
        finally:
            con.close()
        self.assertTrue(result["safety_backup"])
        self.assertTrue(Path(result["safety_backup"]).is_file())


if __name__ == "__main__":
    unittest.main()
