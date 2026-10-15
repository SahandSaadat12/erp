from .connection import get_connection


# ==========================================================
# Dashboard Statistics
# ==========================================================

CANCELED_CONTRACT_STATUSES = ("Canceled", "Cancelled")   # lookups use "Canceled"
CANCELED_PROJECT_STATUSES = ("Cancelled", "Canceled")


def get_dashboard_stats():
    connection = get_connection()
    try:
        return _dashboard_stats(connection)
    finally:
        connection.close()


def _dashboard_stats(connection):
    cursor = connection.cursor()

    # ======================================================
    # Total Projects
    # ======================================================

    cursor.execute("""
        SELECT COUNT(*)
        FROM projects
    """)

    total_projects = cursor.fetchone()[0] or 0

    # ======================================================
    # Active Projects
    # ======================================================

    cursor.execute("""
        SELECT COUNT(*)
        FROM projects
        WHERE project_status IN (
            'Open',
            'In Progress',
            'Active'
        )
    """)

    active_projects = cursor.fetchone()[0] or 0

    # ======================================================
    # Completed Projects
    # ======================================================

    cursor.execute("""
        SELECT COUNT(*)
        FROM projects
        WHERE project_status = 'Completed'
    """)

    completed_projects = cursor.fetchone()[0] or 0

    # ======================================================
    # Revenue
    # ======================================================

    cursor.execute("""
        SELECT
            COALESCE(SUM(expected_price), 0)
        FROM projects
        WHERE COALESCE(project_status, '') NOT IN ('Cancelled', 'Canceled')
    """)

    # This is planned/expected project value, not collected revenue.
    revenue = cursor.fetchone()[0] or 0

    # ======================================================
    # Overall Project Progress   (business rule DASH-02)
    # ======================================================
    #
    # Arithmetic mean of the eligible projects' own progress; every eligible
    # project counts equally.  A project's progress uses its phase weights
    # (Skipped / Cancelled phases ignored), exactly like the overview below.
    # Eligible = every project that is not Cancelled (Completed projects
    # count at their recorded progress).  A project with no counted phases,
    # or whose phase weights add up to 0, has no recorded progress and counts
    # as 0 % - it is never silently treated as completed.  A phase whose
    # progress is NULL counts as 0 %.  Each project value is limited to 0-100.

    cursor.execute("""
        SELECT AVG(MIN(100.0, MAX(0.0, project_progress)))
        FROM (
            SELECT COALESCE(
                       SUM(ph.percentage * COALESCE(ph.progress, 0))
                       / NULLIF(SUM(ph.percentage), 0),
                       0
                   ) AS project_progress
            FROM projects p
            LEFT JOIN project_phases ph
                   ON ph.project_id = p.id
                  AND ph.status NOT IN ('Skipped', 'Cancelled')
            WHERE COALESCE(p.project_status, '') NOT IN ('Cancelled', 'Canceled')
            GROUP BY p.id
        )
    """)

    overall_progress = cursor.fetchone()[0] or 0

    # ======================================================
    # Contracts / Expenses totals
    # ======================================================

    # DASH-01: canceled contracts are excluded from the active totals; their
    # historical value is reported separately and never deleted.
    cursor.execute("""
        SELECT
            COALESCE(SUM(contract_value), 0),
            COALESCE(SUM(paid_amount), 0)
        FROM contracts
        WHERE COALESCE(status, '') NOT IN ('Canceled', 'Cancelled')
    """)

    contracts_value, contracts_paid = cursor.fetchone()

    cursor.execute("""
        SELECT
            COALESCE(SUM(contract_value), 0),
            COALESCE(SUM(paid_amount), 0)
        FROM contracts
        WHERE COALESCE(status, '') IN ('Canceled', 'Cancelled')
    """)

    canceled_contracts_value, canceled_contracts_paid = cursor.fetchone()

    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
        WHERE COALESCE(status, 'Pending') <> 'Cancelled'
    """)

    expenses_total = cursor.fetchone()[0] or 0

    return {
        "total_projects": total_projects,
        "active_projects": active_projects,
        "completed_projects": completed_projects,
        "revenue": revenue,
        "contracts_value": contracts_value or 0,
        "contracts_paid": contracts_paid or 0,
        "canceled_contracts_value": canceled_contracts_value or 0,
        "canceled_contracts_paid": canceled_contracts_paid or 0,
        "expenses_total": expenses_total,
        "overall_progress": overall_progress
    }

# ==========================================================
# Dashboard overview  (charts + tables)
# ==========================================================
#
# One call, one connection, plain SQL.  Every value comes from the
# database - nothing is invented.  Progress uses the same weighted
# formula as the Projects page / Roadmap / Project Controlling window.

from datetime import date, datetime

from persiantools.jdatetime import JalaliDate


def _day(text):
    try:
        return datetime.strptime(str(text)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _month_label(year, month):
    """Gregorian (year, month) -> Jalali 'YYYY/MM' label."""
    try:
        j = JalaliDate.to_jalali(year, month, 15)
        return f"{j.year}/{j.month:02d}"
    except Exception:
        return f"{year}/{month:02d}"


def get_dashboard_overview(months=12, limit=6):

    connection = get_connection()

    try:
        today = date.today()

        # ---------- status mix ---------------------------------
        status = [
            (r[0] or "Unknown", r[1])
            for r in connection.execute("""
                SELECT project_status, COUNT(*)
                FROM projects
                GROUP BY project_status
                ORDER BY COUNT(*) DESC
            """).fetchall()
        ]

        # ---------- weighted progress per project ---------------
        progress_rows = connection.execute("""
            SELECT p.id, p.project_code, p.project_name, p.project_status,
                   p.end_date, p.priority,
                   COALESCE(
                       SUM(ph.percentage * ph.progress)
                       / NULLIF(SUM(ph.percentage), 0), 0
                   ) AS progress,
                   COUNT(ph.id) AS phase_count
            FROM projects p
            LEFT JOIN project_phases ph
                   ON ph.project_id = p.id
                  AND ph.status NOT IN ('Skipped', 'Cancelled')
            GROUP BY p.id
        """).fetchall()

        projects = []
        for r in progress_rows:
            end = _day(r[4])
            projects.append({
                "id": r[0], "code": r[1], "name": r[2], "status": r[3],
                "end_date": r[4], "priority": r[5],
                "progress": float(r[6] or 0), "phases": r[7],
                "days_left": (end - today).days if end else None,
            })

        # ---------- expenses by category ------------------------
        categories = [
            (r[0] or "Uncategorised", float(r[1] or 0))
            for r in connection.execute("""
                SELECT category, SUM(amount)
                FROM expenses
                WHERE COALESCE(status, 'Pending') <> 'Cancelled'
                GROUP BY category
                HAVING SUM(amount) > 0
                ORDER BY SUM(amount) DESC
            """).fetchall()
        ]

        # ---------- monthly expense trend (continuous axis) -----
        totals = {
            r[0]: float(r[1] or 0)
            for r in connection.execute("""
                SELECT SUBSTR(expense_date, 1, 7), SUM(amount)
                FROM expenses
                WHERE COALESCE(expense_date, '') <> ''
                  AND COALESCE(status, 'Pending') <> 'Cancelled'
                GROUP BY SUBSTR(expense_date, 1, 7)
            """).fetchall()
        }

        trend = []
        y, m = today.year, today.month
        keys = []
        for _ in range(max(2, int(months))):
            keys.append((y, m))
            m -= 1
            if m == 0:
                y, m = y - 1, 12
        keys.reverse()

        # drop leading empty months so the line starts at real data
        first = next((i for i, (yy, mm) in enumerate(keys)
                      if totals.get(f"{yy}-{mm:02d}", 0) > 0), None)
        if first is not None:
            keys = keys[first:]
            trend = [(_month_label(yy, mm), totals.get(f"{yy}-{mm:02d}", 0))
                     for yy, mm in keys]

        # ---------- contracts (table + paid-vs-value bars) ------
        contract_rows = [
            {"name": r[0], "project": r[1], "value": float(r[2] or 0),
             "paid": float(r[3] or 0), "status": r[4] or ""}
            for r in connection.execute("""
                SELECT c.contract_name, p.project_name,
                       c.contract_value, c.paid_amount, c.status
                FROM contracts c
                LEFT JOIN projects p ON p.id = c.project_id
                ORDER BY c.contract_value DESC
            """).fetchall()
        ]
        # DASH-01: active contracts feed the table/bars; canceled ones are
        # kept in their own list (historical reporting), never double counted.
        contracts = [c for c in contract_rows
                     if c["status"] not in CANCELED_CONTRACT_STATUSES]
        canceled_contracts = [c for c in contract_rows
                              if c["status"] in CANCELED_CONTRACT_STATUSES]

        # ---------- recent expenses -----------------------------
        recent_expenses = [
            {"title": r[0], "project": r[1], "category": r[2],
             "amount": float(r[3] or 0), "date": r[4], "status": r[5]}
            for r in connection.execute("""
                SELECT e.title, p.project_name, e.category,
                       e.amount, e.expense_date, e.status
                FROM expenses e
                LEFT JOIN projects p ON p.id = e.project_id
                ORDER BY e.expense_date DESC, e.id DESC
                LIMIT ?
            """, (int(limit),)).fetchall()
        ]

    finally:
        connection.close()

    open_projects = [p for p in projects
                     if p["status"] not in ("Completed", "Cancelled", "Closed")]

    deadlines = sorted(
        (p for p in open_projects if p["days_left"] is not None),
        key=lambda p: p["days_left"],
    )[:limit]

    return {
        "status": status,
        "projects": sorted(projects, key=lambda p: -p["progress"]),
        "open_projects": open_projects,
        "categories": categories,
        "trend": trend,
        "contracts": contracts,
        "canceled_contracts": canceled_contracts,
        "recent_expenses": recent_expenses,
        "deadlines": deadlines,
        "overdue": sum(1 for p in open_projects
                       if p["days_left"] is not None and p["days_left"] < 0),
    }
