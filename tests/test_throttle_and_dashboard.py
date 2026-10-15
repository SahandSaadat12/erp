"""
Tests for (1) persistent login throttling and (2) dashboard calculations.

Temporary databases and synthetic records only.  Expected dashboard values are
calculated by hand in the comments, independently of the SQL under test.
"""
import sqlite3
import tempfile
import unittest
from datetime import date as real_date
from pathlib import Path
from unittest.mock import patch

try:                                    # pragma: no cover - environment dependent
    import persiantools  # noqa: F401
    PERSIANTOOLS_IS_REAL = True
except ImportError:                     # minimal stand-in so the SQL logic can still be tested;
    import sys, types                   # Jalali month LABELS are then not verified
    from types import SimpleNamespace
    PERSIANTOOLS_IS_REAL = False
    _pt = types.ModuleType("persiantools")
    _jd = types.ModuleType("persiantools.jdatetime")
    _jd.JalaliDate = SimpleNamespace(
        to_jalali=lambda y, m, d: SimpleNamespace(year=y - 621, month=m))
    _pt.jdatetime = _jd
    sys.modules["persiantools"] = _pt
    sys.modules["persiantools.jdatetime"] = _jd

import paths
import db.connection as db_connection
from db.migrations import init_database


class TempDbCase(unittest.TestCase):
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

    def raw(self):
        return sqlite3.connect(self.db_path)


class LoginThrottleTests(TempDbCase):
    def test_failures_count_down_then_lock(self):
        from db import login_throttle as t
        t0 = 1_000_000.0
        lefts = [t.record_failure("Alice", now=t0 + i)[0] for i in range(4)]
        self.assertEqual(lefts, [4, 3, 2, 1])
        self.assertEqual(t.seconds_locked("alice", now=t0 + 4), 0)

        left, locked = t.record_failure("alice", now=t0 + 4)
        self.assertEqual((left, locked), (0, t.LOCKOUT_SECONDS))
        self.assertGreater(t.seconds_locked("ALICE", now=t0 + 5), 0)
        self.assertEqual(t.seconds_locked("alice", now=t0 + 4 + t.LOCKOUT_SECONDS + 1), 0)

    def test_lock_survives_restart_because_it_is_stored_in_the_database(self):
        from db import login_throttle as t
        for i in range(t.MAX_ATTEMPTS):
            t.record_failure("bob", now=2_000_000.0 + i)
        con = self.raw()
        try:
            row = con.execute(
                "SELECT locked_until FROM login_attempts WHERE username='bob'").fetchone()
        finally:
            con.close()
        self.assertIsNotNone(row)
        self.assertGreater(row[0], 2_000_000.0)
        # a "new process" sees the same lock
        self.assertGreater(t.seconds_locked("bob", now=2_000_010.0), 0)

    def test_success_clears_failures_and_users_are_independent(self):
        from db import login_throttle as t
        t.record_failure("carol", now=3_000_000.0)
        t.record_failure("dave", now=3_000_000.0)
        t.clear("carol")
        left, _ = t.record_failure("carol", now=3_000_001.0)
        self.assertEqual(left, t.MAX_ATTEMPTS - 1)          # counter restarted
        left, _ = t.record_failure("dave", now=3_000_001.0)
        self.assertEqual(left, t.MAX_ATTEMPTS - 2)          # dave untouched

    def test_idle_rows_are_purged(self):
        from db import login_throttle as t
        t.record_failure("old-name", now=1_000.0)
        t.record_failure("new-name", now=1_000.0 + 3 * 24 * 3600)
        con = self.raw()
        try:
            names = {r[0] for r in con.execute("SELECT username FROM login_attempts")}
        finally:
            con.close()
        self.assertEqual(names, {"new-name"})

    def test_locking_one_username_does_not_lock_the_others(self):
        """v2.5 used ONE counter for everybody; a lock must now be per username."""
        from db import login_throttle as t
        for i in range(t.MAX_ATTEMPTS):
            t.record_failure("attacker-target", now=5_000_000.0 + i)
        self.assertGreater(t.seconds_locked("attacker-target", now=5_000_010.0), 0)
        self.assertEqual(t.seconds_locked("someone-else", now=5_000_010.0), 0)
        left, locked = t.record_failure("someone-else", now=5_000_011.0)
        self.assertEqual((left, locked), (t.MAX_ATTEMPTS - 1, 0))

    def test_table_is_added_to_an_existing_database(self):
        con = self.raw()
        con.execute("DROP TABLE login_attempts")
        con.commit()
        con.close()
        init_database()                                      # upgrade path
        con = self.raw()
        try:
            self.assertIsNotNone(con.execute(
                "SELECT 1 FROM sqlite_master WHERE name='login_attempts'").fetchone())
            self.assertEqual(con.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        finally:
            con.close()


class _FixedDate(real_date):
    @classmethod
    def today(cls):
        return cls(2026, 10, 12)


class DashboardCalculationTests(TempDbCase):
    def setUp(self):
        super().setUp()
        con = self.raw()
        ex = con.execute
        for i, name in enumerate(["T-A", "T-B", "T-C", "T-D", "T-E"], start=1):
            ex("INSERT INTO phases(phase_name) VALUES (?)", (name,))
        phase_ids = [r[0] for r in con.execute(
            "SELECT id FROM phases WHERE phase_name LIKE 'T-%' ORDER BY id")]

        def project(code, status, price, end):
            return ex(
                "INSERT INTO projects(project_code, project_name, project_status, "
                "expected_price, end_date) VALUES (?,?,?,?,?)",
                (code, "Project " + code, status, price, end)).lastrowid

        p1 = project("P1", "Open", 1000, "2026-10-01")          # overdue by 11 days
        p2 = project("P2", "In Progress", 2000, "2026-11-01")   # 20 days left
        p3 = project("P3", "Completed", 500, "2026-01-01")
        p4 = project("P4", "Cancelled", 700, "2026-12-01")
        p5 = project("P5", "Open", 0, None)                     # no phases
        p6 = project("P6", "Open", 0, None)                     # zero-weight phase

        def phase(project_id, idx, pct, prog, status):
            ex("INSERT INTO project_phases(project_id, phase_id, percentage, progress, status) "
               "VALUES (?,?,?,?,?)", (project_id, phase_ids[idx], pct, prog, status))

        phase(p1, 0, 60, 50, "In Progress")
        phase(p1, 1, 40, 100, "Completed")
        phase(p1, 2, 50, 10, "Skipped")        # ignored
        phase(p2, 0, 100, 20, "In Progress")
        phase(p3, 0, 100, 100, "Completed")
        phase(p4, 0, 100, 50, "Cancelled")     # ignored -> no weights
        phase(p6, 0, 0, 80, "Pending")         # weight 0 -> progress 0, no crash

        def contract(project_id, name, value, paid, status):
            ex("INSERT INTO contracts(project_id, contract_name, contract_value, paid_amount, status) "
               "VALUES (?,?,?,?,?)", (project_id, name, value, paid, status))

        contract(p1, "C1", 1000, 400, "Active")
        contract(p3, "C2", 500, 500, "Completed")
        contract(p2, "C3", 300, 0, "Canceled")      # DASH-01: not part of active totals

        def expense(project_id, title, cat, amount, day, status):
            ex("INSERT INTO expenses(project_id, title, category, amount, expense_date, status) "
               "VALUES (?,?,?,?,?,?)", (project_id, title, cat, amount, day, status))

        expense(p1, "E1", "Materials", 100, "2026-08-05", "Paid")
        expense(p1, "E2", "Materials", 50, "2026-08-20", "Pending")
        expense(p2, "E3", "Transport", 200, "2026-09-03", "Paid")
        expense(p2, "E4", "Transport", 999, "2026-09-10", "Cancelled")   # excluded everywhere
        expense(p2, "E5", "Software", 25.5, "", "Paid")                  # no date: not in trend
        con.commit()
        con.close()

    # --- get_dashboard_stats ---------------------------------------------
    def test_stats_counts_revenue_contracts_and_expenses(self):
        from db.dashboard import get_dashboard_stats
        s = get_dashboard_stats()
        self.assertEqual(s["total_projects"], 6)
        self.assertEqual(s["active_projects"], 4)        # Open: P1,P5,P6 + In Progress: P2
        self.assertEqual(s["completed_projects"], 1)     # P3
        self.assertAlmostEqual(s["revenue"], 3500)       # 1000+2000+500 (cancelled P4 excluded)
        self.assertAlmostEqual(s["contracts_value"], 1500)       # C1 + C2, C3 canceled
        self.assertAlmostEqual(s["contracts_paid"], 900)
        self.assertAlmostEqual(s["canceled_contracts_value"], 300)   # reported separately
        self.assertAlmostEqual(s["canceled_contracts_paid"], 0)
        self.assertAlmostEqual(s["expenses_total"], 375.5)   # 100+50+200+25.5

    def test_overall_progress_is_equal_weight_mean_of_non_cancelled_projects(self):
        from db.dashboard import get_dashboard_stats
        # eligible: P1=70, P2=20, P3=100, P5 (no phases)=0, P6 (zero weight)=0 ; P4 cancelled
        # (70 + 20 + 100 + 0 + 0) / 5 = 38
        self.assertAlmostEqual(get_dashboard_stats()["overall_progress"], 38.0)

    def test_stats_on_an_empty_database_are_zero_not_errors(self):
        con = self.raw()
        for table in ("expenses", "contracts", "project_phases", "projects"):
            con.execute(f"DELETE FROM {table}")
        con.commit()
        con.close()
        from db.dashboard import get_dashboard_stats
        s = get_dashboard_stats()
        self.assertEqual((s["total_projects"], s["revenue"], s["overall_progress"]), (0, 0, 0))

    # --- get_dashboard_overview ------------------------------------------
    def _overview(self):
        import db.dashboard as dash
        with patch.object(dash, "date", _FixedDate):
            return dash.get_dashboard_overview(months=12, limit=6)

    def test_status_mix(self):
        mix = dict(self._overview()["status"])
        self.assertEqual(mix, {"Open": 3, "In Progress": 1, "Completed": 1, "Cancelled": 1})

    def test_per_project_weighted_progress_and_phase_counts(self):
        by_code = {p["code"]: p for p in self._overview()["projects"]}
        expected = {"P1": (70, 2), "P2": (20, 1), "P3": (100, 1),
                    "P4": (0, 0), "P5": (0, 0),
                    "P6": (0, 1)}      # zero-weight phase: progress 0, but still counted as a phase
        for code, (progress, phases) in expected.items():
            self.assertAlmostEqual(by_code[code]["progress"], progress, msg=code)
            self.assertEqual(by_code[code]["phases"], phases, msg=code)

    def test_expense_categories_exclude_cancelled_and_sort_descending(self):
        cats = self._overview()["categories"]
        self.assertEqual([c[0] for c in cats], ["Transport", "Materials", "Software"])
        self.assertAlmostEqual(cats[0][1], 200)
        self.assertAlmostEqual(cats[1][1], 150)
        self.assertAlmostEqual(cats[2][1], 25.5)

    def test_monthly_trend_starts_at_first_real_month_and_skips_cancelled(self):
        trend = self._overview()["trend"]
        self.assertEqual([v for _, v in trend], [150, 200, 0])    # Aug, Sep, Oct 2026
        self.assertEqual(len({label for label, _ in trend}), 3)

    def test_overview_contracts_exclude_canceled_but_keep_them_separately(self):
        o = self._overview()
        self.assertEqual([c["name"] for c in o["contracts"]], ["C1", "C2"])
        self.assertEqual([c["name"] for c in o["canceled_contracts"]], ["C3"])

    def test_deadlines_and_overdue_only_consider_open_projects(self):
        o = self._overview()
        self.assertEqual(o["overdue"], 1)                         # P1 only
        self.assertEqual([(p["code"], p["days_left"]) for p in o["deadlines"]],
                         [("P1", -11), ("P2", 20)])
        open_codes = {p["code"] for p in o["open_projects"]}
        self.assertEqual(open_codes, {"P1", "P2", "P5", "P6"})    # not Completed / Cancelled


class DashboardRuleEdgeTests(TempDbCase):
    """DASH-02 edge cases, each with its own tiny hand-calculated data set."""

    def _seed(self, projects):
        """projects: list of (status, [(pct, progress, phase_status), ...])"""
        con = self.raw()
        phase_ids = []
        for i in range(4):
            con.execute("INSERT INTO phases(phase_name) VALUES (?)", (f"E-{i}",))
        phase_ids = [r[0] for r in con.execute(
            "SELECT id FROM phases WHERE phase_name LIKE 'E-%' ORDER BY id")]
        for n, (status, phases) in enumerate(projects, start=1):
            pid = con.execute(
                "INSERT INTO projects(project_code, project_name, project_status) VALUES (?,?,?)",
                (f"X{n}", f"X{n}", status)).lastrowid
            for i, (pct, prog, pstatus) in enumerate(phases):
                con.execute(
                    "INSERT INTO project_phases(project_id, phase_id, percentage, progress, status) "
                    "VALUES (?,?,?,?,?)", (pid, phase_ids[i], pct, prog, pstatus))
        con.commit()
        con.close()

    def _overall(self):
        from db.dashboard import get_dashboard_stats
        return get_dashboard_stats()["overall_progress"]

    def test_only_cancelled_projects_gives_zero(self):
        self._seed([("Cancelled", [(100, 100, "Completed")])])
        self.assertEqual(self._overall(), 0)

    def test_project_without_phases_counts_as_zero_not_completed(self):
        # A: 100 %,  B: no phases -> 0 %  => mean 50
        self._seed([("Completed", [(100, 100, "Completed")]), ("Open", [])])
        self.assertAlmostEqual(self._overall(), 50.0)

    def test_equal_weight_per_project_not_per_phase(self):
        # A has one phase at 100 %, B has three phases at 0 % -> mean(100, 0) = 50,
        # NOT the pooled phase average (100*1 + 0*3)/4 = 25
        self._seed([("Open", [(100, 100, "Completed")]),
                    ("Open", [(40, 0, "Pending"), (30, 0, "Pending"), (30, 0, "Pending")])])
        self.assertAlmostEqual(self._overall(), 50.0)

    def test_missing_phase_progress_counts_as_zero(self):
        # phases 50 % @100 and 50 % @NULL -> project 50 ; mean with a 100 % project = 75
        self._seed([("Open", [(100, 100, "Completed")]),
                    ("Open", [(50, 100, "Completed"), (50, None, "Pending")])])
        self.assertAlmostEqual(self._overall(), 75.0)

    def test_out_of_range_progress_is_limited_to_0_100(self):
        self._seed([("Open", [(100, 150, "In Progress")]),      # clamp -> 100
                    ("Open", [(100, -20, "In Progress")])])      # clamp -> 0
        self.assertAlmostEqual(self._overall(), 50.0)

    def test_skipped_and_cancelled_phases_do_not_dilute_progress(self):
        self._seed([("Open", [(50, 80, "Completed"), (50, 10, "Skipped")])])
        self.assertAlmostEqual(self._overall(), 80.0)

    def test_archived_project_and_children_leave_the_dashboard(self):
        from db.users import create_first_admin
        from db.history import set_session_user
        from db.archive import archive_cascade, create_archive_table
        create_archive_table()      # the app creates it at start-up (database.setup_database)
        from db.dashboard import get_dashboard_stats
        create_first_admin("Admin", "adminx", "a-very-long-password-1")
        con = self.raw()
        uid = con.execute("SELECT id FROM users WHERE username='adminx'").fetchone()[0]
        con.close()
        self._seed([("Open", [(100, 100, "Completed")]), ("Open", [(100, 0, "Pending")])])
        con = self.raw()
        pid = con.execute("SELECT id FROM projects WHERE project_code='X1'").fetchone()[0]
        con.execute("INSERT INTO contracts(project_id, contract_name, contract_value, paid_amount, status) "
                    "VALUES (?, 'CX', 700, 100, 'Active')", (pid,))
        con.execute("INSERT INTO expenses(project_id, title, category, amount, status) "
                    "VALUES (?, 'EX', 'Materials', 40, 'Paid')", (pid,))
        con.commit()
        con.close()
        before = get_dashboard_stats()
        self.assertEqual(before["total_projects"], 2)
        self.assertAlmostEqual(before["contracts_value"], 700)
        set_session_user(uid, "adminx")
        archive_cascade("projects", pid)
        after = get_dashboard_stats()
        self.assertEqual(after["total_projects"], 1)
        self.assertAlmostEqual(after["contracts_value"], 0)
        self.assertAlmostEqual(after["expenses_total"], 0)
        self.assertAlmostEqual(after["overall_progress"], 0.0)   # only X2 (0 %) remains


if __name__ == "__main__":
    unittest.main()
