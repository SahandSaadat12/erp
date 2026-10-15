from .connection import get_connection
from .permissions import require_session_permission


def _validated_amount(value):
    """Return a finite, non-negative expense amount or raise ValueError.

    Commas are accepted for display-formatted numeric input. Currency symbols
    and arbitrary text are deliberately rejected instead of silently summing
    to zero in SQLite.
    """
    from decimal import Decimal, InvalidOperation
    import math

    if isinstance(value, bool) or value is None:
        raise ValueError("Expense amount must be a valid non-negative number.")
    try:
        amount = Decimal(str(value).strip().replace(",", ""))
    except (InvalidOperation, ValueError):
        raise ValueError("Expense amount must be a valid non-negative number.")
    if not amount.is_finite() or amount < 0:
        raise ValueError("Expense amount must be a finite, non-negative number.")
    return float(amount)


def _validated_status(status):
    value = str(status or "Pending").strip()
    if value not in {"Pending", "Paid", "Cancelled"}:
        raise ValueError("Expense status must be Pending, Paid, or Cancelled.")
    return value


# ==========================================================
# Create Expenses Table
# ==========================================================

def create_expenses_table():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            project_phase_id INTEGER,
            title TEXT,
            category TEXT,
            amount REAL NOT NULL,
            expense_date TEXT,
            description TEXT,
            paid_by TEXT,
            status TEXT DEFAULT 'Pending',

            FOREIGN KEY (project_id)
                REFERENCES projects(id)
                ON DELETE CASCADE,

            FOREIGN KEY (project_phase_id)
                REFERENCES project_phases(id)
                ON DELETE SET NULL
        )
    """)

    connection.commit()
    connection.close()


# ==========================================================
# Migrate Expenses Table
# ==========================================================

def migrate_expenses_table():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("PRAGMA table_info(expenses)")

    columns = [
        column[1]
        for column in cursor.fetchall()
    ]

    # ------------------------------------------------------
    # Add title
    # ------------------------------------------------------

    if "title" not in columns:

        cursor.execute("""
            ALTER TABLE expenses
            ADD COLUMN title TEXT
        """)

    # ------------------------------------------------------
    # Add paid_by
    # ------------------------------------------------------

    if "paid_by" not in columns:

        cursor.execute("""
            ALTER TABLE expenses
            ADD COLUMN paid_by TEXT
        """)

    # ------------------------------------------------------
    # Add status
    # ------------------------------------------------------

    if "status" not in columns:

        cursor.execute("""
            ALTER TABLE expenses
            ADD COLUMN status TEXT DEFAULT 'Pending'
        """)

    # ------------------------------------------------------
    # Add project_phase_id
    # ------------------------------------------------------

    if "project_phase_id" not in columns:

        cursor.execute("""
            ALTER TABLE expenses
            ADD COLUMN project_phase_id INTEGER
        """)

    connection.commit()
    connection.close()


# ==========================================================
# Insert Expense
# ==========================================================

def insert_expense(
    project_id,
    project_phase_id,
    title,
    expense_date,
    category,
    description,
    amount,
    paid_by,
    status="Pending"
):

    amount = _validated_amount(amount)
    status = _validated_status(status)

    connection = get_connection()

    try:
        require_session_permission(connection, "expenses.create")

        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO expenses (
                project_id,
                project_phase_id,
                title,
                expense_date,
                category,
                description,
                amount,
                paid_by,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            project_id,
            project_phase_id,
            title,
            expense_date,
            category,
            description,
            amount,
            paid_by,
            status
        ))

        connection.commit()

    finally:
        connection.close()


# ==========================================================
# Get All Expenses
# ==========================================================

def get_expenses():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            expenses.id,
            expenses.title,
            expenses.expense_date,
            projects.project_name,
            phases.phase_name,
            expenses.category,
            expenses.description,
            expenses.amount,
            expenses.paid_by,
            expenses.status

        FROM expenses

        LEFT JOIN projects
            ON expenses.project_id = projects.id

        LEFT JOIN project_phases
            ON expenses.project_phase_id = project_phases.id

        LEFT JOIN phases
            ON project_phases.phase_id = phases.id

        ORDER BY expenses.id DESC
    """)

    result = cursor.fetchall()

    connection.close()

    return result

# ==========================================================
# Search Expenses
# ==========================================================

def search_expenses(
    keyword="",
    project="All Projects",
    category="All",
    status="All",
    date_start=None,
    date_end=None
):


    connection = get_connection()
    cursor = connection.cursor()

    query = """
        SELECT
            expenses.id,
            expenses.title,
            expenses.expense_date,
            projects.project_name,
            phases.phase_name,
            expenses.category,
            expenses.description,
            expenses.amount,
            expenses.paid_by,
            expenses.status

        FROM expenses

        LEFT JOIN projects
            ON expenses.project_id = projects.id

        LEFT JOIN project_phases
            ON expenses.project_phase_id = project_phases.id

        LEFT JOIN phases
            ON project_phases.phase_id = phases.id

        WHERE 1=1
    """

    params = []

    # ======================================================
    # Keyword Search
    # ======================================================

    if keyword:

        query += """
            AND (
                expenses.title LIKE ?
                OR expenses.description LIKE ?
                OR projects.project_name LIKE ?
                OR phases.phase_name LIKE ?
                OR expenses.category LIKE ?
                OR expenses.paid_by LIKE ?
                OR expenses.status LIKE ?
            )
        """

        search_value = f"%{keyword}%"

        params.extend([
            search_value,
            search_value,
            search_value,
            search_value,
            search_value,
            search_value,
            search_value
        ])

    # ======================================================
    # Project Filter
    # ======================================================

    if project != "All Projects":

        query += """
            AND projects.project_name = ?
        """

        params.append(project)

    # ======================================================
    # Category Filter
    # ======================================================

    if category != "All":

        query += """
            AND expenses.category = ?
        """

        params.append(category)

    # ======================================================
    # Status Filter
    # ======================================================

    if status != "All":

        query += """
            AND expenses.status = ?
        """

        params.append(status)

    # ======================================================
    # Date Filter
    # ======================================================

    if date_start and date_end:

        query += """
            AND expenses.expense_date >= ?
            AND expenses.expense_date <= ?
        """

        params.extend([
            date_start,
            date_end
        ])

    # ======================================================
    # Order
    # ======================================================

    query += """
        ORDER BY expenses.id DESC
    """

    cursor.execute(
        query,
        params
    )

    result = cursor.fetchall()

    connection.close()

    return result


# ==========================================================
# Get Expense By ID
# ==========================================================

def get_expense_by_id(expense_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            project_id,
            project_phase_id,
            title,
            expense_date,
            category,
            description,
            amount,
            paid_by,
            status

        FROM expenses

        WHERE id = ?
    """, (expense_id,))

    result = cursor.fetchone()

    connection.close()

    return result


# ==========================================================
# Update Expense
# ==========================================================

def update_expense(
    expense_id,
    project_id,
    project_phase_id,
    title,
    expense_date,
    category,
    description,
    amount,
    paid_by,
    status
):

    amount = _validated_amount(amount)
    status = _validated_status(status)

    connection = get_connection()

    try:
        require_session_permission(connection, "expenses.edit")

        cursor = connection.cursor()

        cursor.execute("""
            UPDATE expenses

            SET
                project_id = ?,
                project_phase_id = ?,
                title = ?,
                expense_date = ?,
                category = ?,
                description = ?,
                amount = ?,
                paid_by = ?,
                status = ?

            WHERE id = ?
        """, (
            project_id,
            project_phase_id,
            title,
            expense_date,
            category,
            description,
            amount,
            paid_by,
            status,
            expense_id
        ))

        connection.commit()

    finally:
        connection.close()


# ==========================================================
# Delete Expense
# ==========================================================

def delete_expense(expense_id):

    connection = get_connection()

    try:
        require_session_permission(connection, "expenses.delete")
    except Exception:
        connection.close()
        raise

    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM expenses

        WHERE id = ?
    """, (expense_id,))

    connection.commit()
    connection.close()


# ==========================================================
# Get Expense Total
# ==========================================================

def get_expense_total():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            COALESCE(SUM(amount), 0)

        FROM expenses
        WHERE COALESCE(status, 'Pending') <> 'Cancelled'
    """)

    result = cursor.fetchone()

    connection.close()

    if result:
        return result[0]

    return 0


# ==========================================================
# Get Expense Projects
# ==========================================================

def get_expense_projects():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            project_name

        FROM projects

        ORDER BY project_name
    """)

    result = cursor.fetchall()

    connection.close()

    return result


# ==========================================================
# Get Expense Phases
# ==========================================================

def get_expense_phases(project_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            project_phases.id,
            phases.phase_name

        FROM project_phases

        JOIN phases
            ON project_phases.phase_id = phases.id

        WHERE project_phases.project_id = ?

        ORDER BY
            project_phases.sort_order IS NULL,
            project_phases.sort_order,
            project_phases.id
    """, (project_id,))

    result = cursor.fetchall()

    connection.close()

    return result


# ==========================================================
# Get Project Actual Price
# ==========================================================

def get_project_actual_price(project_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            COALESCE(SUM(amount), 0)

        FROM expenses

        WHERE project_id = ?
          AND COALESCE(status, 'Pending') <> 'Cancelled'
    """, (project_id,))

    result = cursor.fetchone()

    connection.close()

    if result:
        return result[0]

    return 0


# ==========================================================
# Get Phase Actual Price
# ==========================================================

def get_phase_actual_price(project_phase_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            COALESCE(SUM(amount), 0)

        FROM expenses

        WHERE project_phase_id = ?
          AND COALESCE(status, 'Pending') <> 'Cancelled'
    """, (project_phase_id,))

    result = cursor.fetchone()

    connection.close()

    if result:
        return result[0]

    return 0


# NOTE: table creation / migration used to run here automatically on
# import (a side effect of just importing this module). That's been
# removed - db/migrations.py.init_database() is the single place that
# creates/migrates the schema now. create_expenses_table() and
# migrate_expenses_table() are still here, just not auto-called.

def get_expense_phases(project_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            project_phases.id,
            phases.phase_name
        FROM project_phases
        JOIN phases
            ON project_phases.phase_id = phases.id
        WHERE project_phases.project_id = ?
        ORDER BY
            project_phases.sort_order IS NULL,
            project_phases.sort_order,
            project_phases.id
    """, (project_id,))

    result = cursor.fetchall()

    connection.close()

    return result