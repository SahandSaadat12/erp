"""Tests for monetary validation and calculation correctness."""
import sqlite3
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import paths
import db.connection as db_connection
from db.migrations import init_database
from db.contracts import insert_contract, get_contract_by_id, update_contract, _validated_amount as contract_validated_amount
from db.expenses import _validated_amount, get_expense_total, get_project_actual_price
from db.users import create_first_admin
from db.history import set_session_user


def _setup_auth_session(db_path):
    """Create an admin user and set up an authenticated session."""
    from db.connection import get_connection
    con = get_connection()
    try:
        # Check if admin already exists
        user = con.execute("SELECT id FROM users WHERE username = ?", ("admin",)).fetchone()
        if not user:
            create_first_admin("Test Admin", "admin", "admin-pass-123")
        set_session_user(1, "admin")
    finally:
        con.close()


class FinancialValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.db_path = str(self.base / "erp.db")
        self.path_patch = patch.object(paths, "DB_PATH", self.db_path)
        self.connection_patch = patch.object(db_connection, "DB_PATH", self.db_path)
        self.path_patch.start()
        self.connection_patch.start()
        init_database()
        _setup_auth_session(self.db_path)

    def tearDown(self):
        self.connection_patch.stop()
        self.path_patch.stop()
        self.temp.cleanup()

    def _create_project(self):
        con = sqlite3.connect(self.db_path)
        con.execute("INSERT INTO projects(project_code, project_name, project_status) VALUES ('T-1','Test','Open')")
        pid = con.execute("SELECT id FROM projects WHERE project_code='T-1'").fetchone()[0]
        con.commit()
        con.close()
        return pid

    def test_contract_amount_validation_rejects_invalid(self):
        for invalid in ("abc", -1, float("nan"), float("inf"), None, True):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    contract_validated_amount(invalid)

    def test_contract_amount_validation_accepts_valid(self):
        self.assertAlmostEqual(contract_validated_amount("1,234,567"), 1234567.0)
        self.assertAlmostEqual(contract_validated_amount(0), 0.0)
        self.assertAlmostEqual(contract_validated_amount(999999), 999999.0)

    def test_expense_amount_validation_rejects_invalid(self):
        for invalid in ("abc", -1, float("nan"), float("inf"), None, True):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    _validated_amount(invalid)

    def test_expense_amount_validation_accepts_valid(self):
        self.assertAlmostEqual(_validated_amount("1,234.50"), 1234.5)
        self.assertAlmostEqual(_validated_amount(0), 0.0)

    def test_insert_contract_with_negative_amount_rejected(self):
        pid = self._create_project()
        with self.assertRaises(ValueError):
            insert_contract(pid, None, "Test", "C-1", -100, 0, None, None, "Active", None)

    def test_update_contract_with_invalid_amount_rejected(self):
        pid = self._create_project()
        cid = insert_contract(pid, None, "Test", "C-1", 1000, 0, None, None, "Active", None)
        with self.assertRaises(ValueError):
            update_contract(cid, pid, None, "Test", "C-1", -50, None, None, None, None, None)

    def test_expense_total_excludes_cancelled(self):
        pid = self._create_project()
        con = sqlite3.connect(self.db_path)
        con.executemany(
            "INSERT INTO expenses(project_id, title, amount, status) VALUES (?, ?, ?, ?)",
            [(pid, "Paid", 100, "Paid"), (pid, "Pending", 200, "Pending"), (pid, "Cancelled", 999, "Cancelled")],
        )
        con.commit()
        con.close()
        self.assertEqual(get_expense_total(), 300.0)
        self.assertEqual(get_project_actual_price(pid), 300.0)

    def test_repeated_decimal_additions_no_drift(self):
        total = Decimal("0")
        for _ in range(1000):
            total += Decimal("0.01")
        self.assertEqual(total, Decimal("10.00"))

    def test_contract_outstanding_balance(self):
        pid = self._create_project()
        cid = insert_contract(pid, None, "Test", "C-1", 1000000, 250000, None, None, "Active", None)
        row = get_contract_by_id(cid)
        outstanding = float(Decimal(str(row[5])) - Decimal(str(row[6])))
        self.assertEqual(outstanding, 750000.0)


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.db_path = str(self.base / "erp.db")
        self.path_patch = patch.object(paths, "DB_PATH", self.db_path)
        self.connection_patch = patch.object(db_connection, "DB_PATH", self.db_path)
        self.path_patch.start()
        self.connection_patch.start()
        init_database()
        _setup_auth_session(self.db_path)

    def tearDown(self):
        self.connection_patch.stop()
        self.path_patch.stop()
        self.temp.cleanup()

    def _create_project(self):
        con = sqlite3.connect(self.db_path)
        con.execute("INSERT INTO projects(project_code, project_name, project_status) VALUES ('T-1','Test','Open')")
        pid = con.execute("SELECT id FROM projects WHERE project_code='T-1'").fetchone()[0]
        con.commit()
        con.close()
        return pid

    def test_progress_validation_rejects_out_of_range(self):
        from db.connection import validate_progress
        for invalid in (-1, 101, 1000, -0.1):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    validate_progress(invalid)

    def test_progress_validation_accepts_valid(self):
        from db.connection import validate_progress
        validate_progress(0)
        validate_progress(50)
        validate_progress(100)
        validate_progress(None)

    def test_date_validation_rejects_invalid(self):
        from db.connection import validate_date
        for invalid in ("2026-13-01", "2026-02-30", "abc", "2026/01/01"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    validate_date(invalid)

    def test_date_validation_accepts_valid(self):
        from db.connection import validate_date
        validate_date("2026-01-15")
        validate_date("2026-12-31")
        validate_date(None)
        validate_date("")

    def test_insert_project_with_invalid_date_rejected(self):
        from db.projects import insert_project
        with self.assertRaises(ValueError):
            insert_project("T-1", "Test", start_date="invalid", end_date=None)

    def test_insert_project_with_invalid_progress_phase_rejected(self):
        from db.phases import insert_project_phase, update_project_phase
        pid = self._create_project()
        con = sqlite3.connect(self.db_path)
        con.execute("INSERT INTO phases(phase_name) VALUES ('Test Phase')")
        fid = con.execute("SELECT id FROM phases WHERE phase_name='Test Phase'").fetchone()[0]
        con.commit()
        con.close()
        ppid = insert_project_phase(pid, fid, 25)
        with self.assertRaises(ValueError):
            update_project_phase(ppid, 25, 101)


class DashboardCalculationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.db_path = str(self.base / "erp.db")
        self.path_patch = patch.object(paths, "DB_PATH", self.db_path)
        self.connection_patch = patch.object(db_connection, "DB_PATH", self.db_path)
        self.path_patch.start()
        self.connection_patch.start()
        init_database()
        _setup_auth_session(self.db_path)

    def tearDown(self):
        self.connection_patch.stop()
        self.path_patch.stop()
        self.temp.cleanup()

    def _create_project(self, code="T-1", name="Test", status="Open"):
        con = sqlite3.connect(self.db_path)
        con.execute("INSERT INTO projects(project_code, project_name, project_status) VALUES (?,?,?)", (code, name, status))
        pid = con.execute("SELECT id FROM projects WHERE project_code=?", (code,)).fetchone()[0]
        con.commit()
        con.close()
        return pid

    def _add_phase(self, pid, name, pct, prog):
        con = sqlite3.connect(self.db_path)
        con.execute("INSERT INTO phases(phase_name) VALUES (?)", (name,))
        fid = con.execute("SELECT id FROM phases WHERE phase_name=?", (name,)).fetchone()[0]
        con.execute("INSERT INTO project_phases(project_id, phase_id, percentage, progress, status) VALUES (?,?,?,?,?)", (pid, fid, pct, prog, "In Progress"))
        con.commit()
        con.close()

    def test_weighted_progress_calculation(self):
        from db.projects import get_projects
        pid = self._create_project("WP-1", "Weighted Test")
        self._add_phase(pid, "Phase A", 50, 80)
        self._add_phase(pid, "Phase B", 50, 40)
        projects = get_projects()
        wp = next((p for p in projects if p[0] == "WP-1"), None)
        self.assertIsNotNone(wp)
        expected = (50 * 80 + 50 * 40) / 100
        self.assertAlmostEqual(float(wp[4]), expected, places=5)

    def test_project_with_no_phases(self):
        from db.projects import get_projects
        self._create_project("NP-1", "No Phases")
        projects = get_projects()
        np = next((p for p in projects if p[0] == "NP-1"), None)
        self.assertIsNotNone(np)
        self.assertEqual(float(np[4]), 0)

    def test_dashboard_stats_counts(self):
        from db.dashboard import get_dashboard_stats
        self._create_project("DS-1", "Open Project", "Open")
        self._create_project("DS-2", "Completed Project", "Completed")
        self._create_project("DS-3", "In Progress Project", "In Progress")
        stats = get_dashboard_stats()
        self.assertGreaterEqual(stats["total_projects"], 3)
        self.assertGreaterEqual(stats["active_projects"], 2)
        self.assertGreaterEqual(stats["completed_projects"], 1)

    def test_contract_outstanding_in_dashboard(self):
        from db.dashboard import get_dashboard_stats
        from db.contracts import insert_contract
        pid = self._create_project("CT-1", "Contract Test")
        insert_contract(pid, None, "Test Contract", "C-1", 1000000, 300000, None, None, "Active", None)
        stats = get_dashboard_stats()
        self.assertGreaterEqual(float(stats["contracts_value"]), 1000000)
        self.assertGreaterEqual(float(stats["contracts_paid"]), 300000)


class LicenseConcurrencyTests(unittest.TestCase):
    def test_concurrent_state_access(self):
        import threading
        import json
        import tempfile
        import os
        from licensing.gate import _load, _save

        tmpdir = tempfile.mkdtemp()
        state_path = os.path.join(tmpdir, "test_state.json")
        test_data = {"code_hash": "abc123", "last_ok": "2026-01-01T00:00:00Z", "last_attempt": "2026-01-01T00:00:00Z", "high_water": "2026-01-01T00:00:00Z", "disabled": False}

        results = []
        errors = []

        def writer():
            try:
                for _ in range(20):
                    _save(state_path, test_data)
                results.append("writer_ok")
            except Exception as e:
                errors.append(str(e))

        def reader():
            try:
                for _ in range(20):
                    _load(state_path)
                results.append("reader_ok")
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=writer), threading.Thread(target=reader)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Errors: {errors}")
        self.assertEqual(len(results), 2)

        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_corrupted_state_file(self):
        import tempfile
        import os
        from licensing.gate import _load

        tmpdir = tempfile.mkdtemp()
        state_path = os.path.join(tmpdir, "corrupt.json")
        with open(state_path, "w") as f:
            f.write("{invalid json")

        result = _load(state_path)
        self.assertIsNone(result)

        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_state_atomic_write(self):
        import tempfile
        import os
        from licensing.gate import _save, _load

        tmpdir = tempfile.mkdtemp()
        state_path = os.path.join(tmpdir, "atomic.json")
        test_data = {"test": "value"}

        _save(state_path, test_data)
        loaded = _load(state_path)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["test"], "value")

        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
