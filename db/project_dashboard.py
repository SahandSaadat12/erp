"""
Data service for the single-project "View Project" dashboard.

Layer order:  SQL (here, 4 small queries)  ->  calculations (here)  ->
              ui/projects/project_dashboard.py (charts + widgets)

Nothing is invented: every number comes from projects / project_phases /
expenses / contracts / documents.  Progress uses the SAME weighted formula
as db/projects.get_projects() and the Roadmap:

    overall = SUM(weight * progress) / SUM(weight)
    (phases whose status is Skipped / Cancelled are ignored)
"""

from datetime import date, datetime

from persiantools.jdatetime import JalaliDate

from .connection import get_connection

EXCLUDED = ("Skipped", "Cancelled")


def _d(text):
    try:
        return datetime.strptime(str(text)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def project_id_by_code(project_code):

    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT id FROM projects WHERE project_code = ?", (project_code,)
        ).fetchone()
        return row[0] if row else None
    finally:
        connection.close()


def get_project_dashboard(project_id):
    """Returns one dict with everything the dashboard needs (or None)."""

    connection = get_connection()

    try:
        head = connection.execute("""
            SELECT p.id, p.project_code, p.project_name, c.company_name,
                   u.full_name, p.project_status, p.priority, p.start_date,
                   p.end_date, COALESCE(p.expected_price, 0), p.project_type,
                   p.description, d.department_name
            FROM projects p
            LEFT JOIN clients c ON p.client_id = c.id
            LEFT JOIN users u ON p.manager_id = u.id
            LEFT JOIN departments d ON p.department_id = d.id
            WHERE p.id = ?
        """, (project_id,)).fetchone()

        if head is None:
            return None

        phase_rows = connection.execute("""
            SELECT pp.id, ph.phase_name, pp.percentage, COALESCE(pp.progress, 0),
                   pp.status, pp.start_date, pp.end_date,
                   COALESCE(pp.expected_price, 0)
            FROM project_phases pp
            JOIN phases ph ON pp.phase_id = ph.id
            WHERE pp.project_id = ?
            ORDER BY pp.sort_order IS NULL, pp.sort_order, pp.id
        """, (project_id,)).fetchall()

        expense_rows = connection.execute("""
            SELECT COALESCE(NULLIF(TRIM(category), ''), 'Other'),
                   COALESCE(amount, 0), expense_date, status, project_phase_id
            FROM expenses WHERE project_id = ?
        """, (project_id,)).fetchall()

        contract_rows = connection.execute("""
            SELECT COALESCE(contract_value, 0), COALESCE(paid_amount, 0), status
            FROM contracts WHERE project_id = ?
        """, (project_id,)).fetchall()

        doc_count = connection.execute(
            "SELECT COUNT(*) FROM documents WHERE project_id = ?", (project_id,)
        ).fetchone()[0]

    finally:
        connection.close()

    today = date.today()

    phase_actual = {}                 # project_phases.id -> money spent
    for _c, amount, _d2, _s, phase_id in expense_rows:
        if phase_id:
            phase_actual[phase_id] = phase_actual.get(phase_id, 0) + float(amount or 0)

    # ---------------------------------------------------------- phases
    phases = []
    for (pid, name, weight, progress, status, start, end, price) in phase_rows:
        end_d = _d(end)
        overdue = bool(
            end_d and end_d < today
            and status not in ("Completed",) + EXCLUDED
            and (progress or 0) < 100
        )
        phases.append({
            "id": pid, "name": name, "weight": float(weight or 0),
            "progress": float(progress or 0), "status": status or "Pending",
            "start": start, "end": end, "price": float(price or 0),
            "actual": phase_actual.get(pid, 0.0),
            "overdue": overdue,
            "days_left": (end_d - today).days if end_d else None,
        })

    active = [p for p in phases if p["status"] not in EXCLUDED]
    total_w = sum(p["weight"] for p in active)
    overall = (
        sum(p["weight"] * p["progress"] for p in active) / total_w
        if total_w else 0.0
    )

    status_counts = {}
    for p in phases:
        status_counts[p["status"]] = status_counts.get(p["status"], 0) + 1

    completed = sum(
        1 for p in phases
        if p["status"] == "Completed" or (p["status"] not in EXCLUDED and p["progress"] >= 100)
    )

    # ---------------------------------------------------------- dates
    start_d, end_d = _d(head[7]), _d(head[8])
    duration = days_left = elapsed_pct = None
    if start_d and end_d and end_d >= start_d:
        duration = (end_d - start_d).days + 1
        days_left = (end_d - today).days
        elapsed_pct = min(100.0, max(0.0, (today - start_d).days / max(duration - 1, 1) * 100))

    # ---------------------------------------------------------- money
    by_category, by_month = {}, {}
    total_expenses = 0.0
    for category, amount, exp_date, _status, _phase in expense_rows:
        amount = float(amount or 0)
        total_expenses += amount
        by_category[category] = by_category.get(category, 0) + amount
        d = _d(exp_date)
        if d:
            j = JalaliDate.to_jalali(d)
            key = (j.year, j.month)
            by_month[key] = by_month.get(key, 0) + amount

    categories = sorted(by_category.items(), key=lambda kv: -kv[1])
    months = []                       # continuous Jalali months, gaps = 0
    if by_month:
        (y, m), (y2, m2) = min(by_month), max(by_month)
        while (y, m) <= (y2, m2):
            months.append((f"{y}/{m:02d}", by_month.get((y, m), 0.0)))
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)

    budget = float(head[9] or 0)
    contract_value = sum(float(r[0]) for r in contract_rows)
    contract_paid = sum(float(r[1]) for r in contract_rows)

    upcoming = sorted(
        [p for p in phases if p["status"] not in EXCLUDED + ("Completed",) and p["end"]],
        key=lambda p: (p["end"] or "9999"),
    )

    return {
        "id": head[0], "code": head[1], "name": head[2],
        "client": head[3], "manager": head[4], "status": head[5],
        "priority": head[6], "start": head[7], "end": head[8],
        "budget": budget, "type": head[10], "description": head[11],
        "department": head[12],
        "progress": overall,
        "phases": phases,
        "phases_total": len(phases),
        "phases_completed": completed,
        "status_counts": status_counts,
        "overdue_count": sum(1 for p in phases if p["overdue"]),
        "duration": duration, "days_left": days_left, "elapsed_pct": elapsed_pct,
        "start_date": start_d, "end_date": end_d,
        "total_expenses": total_expenses,
        "expense_count": len(expense_rows),
        "budget_usage": (total_expenses / budget * 100) if budget else None,
        "remaining_budget": (budget - total_expenses) if budget else None,
        "categories": categories,
        "months": months,
        "contract_value": contract_value,
        "contract_paid": contract_paid,
        "contract_count": len(contract_rows),
        "documents": doc_count,
        "upcoming": upcoming,
    }
