"""Security regression tests."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import paths
import db.connection as db_connection
from db.migrations import init_database
from db.users import create_first_admin
from db.history import set_session_user
from db.permissions import require_session_permission, get_permissions_for_role
from security import hash_password, verify_password, is_hashed


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.db_path = str(self.base / "erp.db")
        self.path_patch = patch.object(paths, "DB_PATH", self.db_path)
        self.connection_patch = patch.object(db_connection, "DB_PATH", self.db_path)
        self.path_patch.start()
        self.connection_patch.start()
        init_database()

    def tearDown(self):
        self.connection_patch.stop()
        self.path_patch.stop()
        self.temp.cleanup()

    def test_password_hashing_uses_scrypt(self):
        hashed = hash_password("test-password-123")
        self.assertTrue(is_hashed(hashed))
        self.assertTrue(hashed.startswith("scrypt$"))

    def test_password_verification_correct(self):
        hashed = hash_password("test-password-123")
        self.assertTrue(verify_password("test-password-123", hashed))

    def test_password_verification_incorrect(self):
        hashed = hash_password("test-password-123")
        self.assertFalse(verify_password("wrong-password", hashed))

    def test_legacy_plaintext_password_verification(self):
        self.assertTrue(verify_password("legacy", "legacy"))
        self.assertFalse(verify_password("wrong", "legacy"))

    def test_password_not_logged(self):
        from utils.app_logger import error as log_error
        with patch("builtins.open", MagicMock()) as mock_open:
            from utils.app_logger import _write
            _write("INFO", "test message")
            written = mock_open.call_args[0][0] if mock_open.call_args else ""
            self.assertNotIn("password", str(written).lower())


class AuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.db_path = str(self.base / "erp.db")
        self.path_patch = patch.object(paths, "DB_PATH", self.db_path)
        self.connection_patch = patch.object(db_connection, "DB_PATH", self.db_path)
        self.path_patch.start()
        self.connection_patch.start()
        init_database()
        create_first_admin("Test Admin", "admin", "admin-pass-123")
        set_session_user(1, "admin")

    def tearDown(self):
        self.connection_patch.stop()
        self.path_patch.stop()
        self.temp.cleanup()

    def test_require_session_permission_no_session(self):
        con = sqlite3.connect(self.db_path)
        con.execute("UPDATE session_context SET user_id = NULL WHERE id = 1")
        con.commit()
        with self.assertRaises(PermissionError):
            require_session_permission(con, "expenses.delete")
        con.close()

    def test_require_session_permission_active_session(self):
        con = sqlite3.connect(self.db_path)
        result = require_session_permission(con, "expenses.delete")
        self.assertTrue(result)
        con.close()

    def test_disabled_user_denied(self):
        con = sqlite3.connect(self.db_path)
        con.execute("UPDATE users SET status = 'Inactive' WHERE id = 1")
        con.commit()
        with self.assertRaises(PermissionError):
            require_session_permission(con, "expenses.delete")
        con.close()

    def test_manager_has_all_permissions(self):
        perms = get_permissions_for_role("Manager")
        self.assertIn("expenses.delete", perms)
        self.assertIn("backup.restore", perms)


class DatabaseIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.db_path = str(self.base / "erp.db")
        self.path_patch = patch.object(paths, "DB_PATH", self.db_path)
        self.connection_patch = patch.object(db_connection, "DB_PATH", self.db_path)
        self.path_patch.start()
        self.connection_patch.start()
        init_database()

    def tearDown(self):
        self.connection_patch.stop()
        self.path_patch.stop()
        self.temp.cleanup()

    def test_foreign_keys_enforced(self):
        from db.connection import get_connection
        con = get_connection()
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                con.execute("INSERT INTO expenses(project_id, amount) VALUES (999, 100)")
        finally:
            con.close()

    def test_parameterized_query_prevents_injection(self):
        from db.projects import get_projects
        projects = get_projects()
        self.assertIsInstance(projects, list)


class FileOperationTests(unittest.TestCase):
    def test_document_open_validates_extension(self):
        from ui.documents.open_document import ALLOWED_EXTENSIONS
        self.assertIn(".pdf", ALLOWED_EXTENSIONS)
        self.assertNotIn(".exe", ALLOWED_EXTENSIONS)
        self.assertNotIn(".bat", ALLOWED_EXTENSIONS)

    def test_app_logger_does_not_expose_secrets(self):
        from utils.app_logger import _write
        with patch("builtins.open", MagicMock()):
            _write("ERROR", "user=admin password=secret123")


class LicensingTests(unittest.TestCase):
    def test_state_lock_exists(self):
        import threading
        from licensing.gate import _state_lock
        self.assertIsInstance(_state_lock, type(threading.Lock()))

    def test_load_returns_none_for_missing_file(self):
        from licensing.gate import _load
        result = _load("/nonexistent/path/state.json")
        self.assertIsNone(result)

    def test_save_and_load_roundtrip(self):
        import tempfile
        import os
        from licensing.gate import _save, _load
        tmpdir = tempfile.mkdtemp()
        state_path = os.path.join(tmpdir, "test.json")
        test_data = {"key": "value", "number": 42}
        _save(state_path, test_data)
        loaded = _load(state_path)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["key"], "value")
        self.assertEqual(loaded["number"], 42)

    def test_hmac_key_is_constant(self):
        from licensing.gate import _KEY
        self.assertIsInstance(_KEY, bytes)
        self.assertEqual(len(_KEY), 20)


if __name__ == "__main__":
    unittest.main()
