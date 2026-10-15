import sqlite3

from .connection import get_connection, connect, validate_date
from .permissions import require_session_permission


# ==========================================================
# Project Insert
# ==========================================================

def insert_project(
    project_code,
    project_name,
    client_id=None,
    project_type=None,
    department_id=None,
    manager_id=None,
    start_date=None,
    end_date=None,
    priority="Medium",
    project_status="Open",
    description=None,
    expected_price=0
):
    validate_date(start_date, "Start date")
    validate_date(end_date, "End date")

    connection = get_connection()

    try:
        require_session_permission(connection, "projects.create")

        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO projects(
                project_code,
                project_name,
                client_id,
                project_type,
                department_id,
                manager_id,
                start_date,
                end_date,
                priority,
                project_status,
                description,
                expected_price
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            project_code,
            project_name,
            client_id,
            project_type,
            department_id,
            manager_id,
            start_date,
            end_date,
            priority,
            project_status,
            description,
            expected_price
        ))

        connection.commit()

        project_id = cursor.lastrowid

        return project_id

    finally:
        connection.close()


# ==========================================================
# Generate Project Code
# ==========================================================

def generate_project_code(project_name):

    connection = get_connection()
    cursor = connection.cursor()

    words = project_name.split()

    prefix = ""

    for word in words:

        if word:
            prefix += word[0].upper()

    prefix = prefix[:3]

    cursor.execute("""
        SELECT project_code
        FROM projects
        WHERE project_code LIKE ?
        ORDER BY project_code DESC
    """, (prefix + "-%",))

    projects = cursor.fetchall()

    connection.close()

    if not projects:
        return f"{prefix}-001"

    numbers = []

    for project in projects:

        code = project[0]

        try:

            number = int(
                code.split("-")[1]
            )

            numbers.append(number)

        except Exception:
            pass

    if numbers:
        next_number = max(numbers) + 1
    else:
        next_number = 1

    return f"{prefix}-{next_number:03d}"


# ==========================================================
# Get Project By Code
# ==========================================================

def get_project_by_code(project_code):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            project_code,
            project_name,
            client_id,
            project_type,
            department_id,
            manager_id,
            start_date,
            end_date,
            priority,
            project_status,
            description,
            expected_price

        FROM projects

        WHERE project_code = ?
    """, (project_code,))

    result = cursor.fetchone()

    connection.close()

    return result


# ==========================================================
# Get Project Details
# ==========================================================

def get_project_details(project_code):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            projects.id,
            projects.project_code,
            projects.project_name,

            clients.company_name,

            projects.project_type,

            departments.department_name,

            users.full_name,

            projects.start_date,
            projects.end_date,

            projects.priority,
            projects.project_status,

            projects.description,
            projects.expected_price

        FROM projects

        LEFT JOIN clients
            ON projects.client_id = clients.id

        LEFT JOIN departments
            ON projects.department_id = departments.id

        LEFT JOIN users
            ON projects.manager_id = users.id

        WHERE projects.project_code = ?
    """, (project_code,))

    result = cursor.fetchone()

    connection.close()

    return result


# ==========================================================
# Update Project
# ==========================================================

def update_project(
    project_id,
    project_code,
    project_name,
    client_id,
    project_type,
    department_id,
    manager_id,
    start_date,
    end_date,
    priority,
    project_status,
    description,
    expected_price
):
    validate_date(start_date, "Start date")
    validate_date(end_date, "End date")

    connection = get_connection()

    try:
        require_session_permission(connection, "projects.edit")

        cursor = connection.cursor()

        cursor.execute("""
            UPDATE projects

            SET
                project_code = ?,
                project_name = ?,
                client_id = ?,
                project_type = ?,
                department_id = ?,
                manager_id = ?,
                start_date = ?,
                end_date = ?,
                priority = ?,
                project_status = ?,
                description = ?,
                expected_price = ?

            WHERE id = ?
        """, (
            project_code,
            project_name,
            client_id,
            project_type,
            department_id,
            manager_id,
            start_date,
            end_date,
            priority,
            project_status,
            description,
            expected_price,
            project_id
        ))

        connection.commit()

    finally:
        connection.close()


# ==========================================================
# Get Projects
# ==========================================================

def get_projects():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            p.project_code,
            p.project_name,
            c.company_name,
            u.full_name,

            COALESCE(
                (
                    SELECT
                        SUM(
                            pp.percentage * pp.progress
                        ) / NULLIF(
                            SUM(pp.percentage),
                            0
                        )

                    FROM project_phases pp

                    WHERE pp.project_id = p.id
                      AND pp.status NOT IN ('Skipped', 'Cancelled')
                ),
                0
            ) AS progress,

            p.project_status,
            p.start_date,
            p.end_date

        FROM projects p

        LEFT JOIN clients c
            ON p.client_id = c.id

        LEFT JOIN users u
            ON p.manager_id = u.id

        ORDER BY p.id DESC
    """)

    result = cursor.fetchall()

    connection.close()

    return result


# ==========================================================
# Remove Project
# ==========================================================

def remove_project(project_id):

    connection = get_connection()

    try:
        require_session_permission(connection, "projects.delete")

        cursor = connection.cursor()

        cursor.execute("""
            DELETE FROM project_phases
            WHERE project_id = ?
              AND COALESCE(status, 'Pending') <> 'Cancelled'
        """, (project_id,))

        cursor.execute("""
            DELETE FROM projects
            WHERE id = ?
        """, (project_id,))

        connection.commit()

    finally:
        connection.close()

    return True


# ==========================================================
# Get Managers
# ==========================================================

def get_managers():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            full_name

        FROM users

        WHERE COALESCE(status, 'Active') = 'Active'

        ORDER BY full_name
    """)

    result = cursor.fetchall()

    connection.close()

    return result


# ==========================================================
# Search Projects
# ==========================================================

def search_projects(
    keyword="",
    manager="All Managers",
    status="All Status",
    date_start=None,
    date_end=None
):

    connection = get_connection()
    cursor = connection.cursor()

    query = """
        SELECT
            p.project_code,
            p.project_name,
            c.company_name,
            u.full_name,

            COALESCE(
                (
                    SELECT
                        SUM(
                            pp.percentage * pp.progress
                        ) / NULLIF(
                            SUM(pp.percentage),
                            0
                        )

                    FROM project_phases pp

                    WHERE pp.project_id = p.id
                      AND pp.status NOT IN ('Skipped', 'Cancelled')
                ),
                0
            ) AS progress,

            p.project_status,
            p.start_date,
            p.end_date

        FROM projects p

        LEFT JOIN clients c
            ON p.client_id = c.id

        LEFT JOIN users u
            ON p.manager_id = u.id

        WHERE 1=1
    """

    params = []

    # ======================================================
    # Keyword Search
    # ======================================================

    if keyword:

        query += """
            AND (
                p.project_code LIKE ?
                OR p.project_name LIKE ?
                OR c.company_name LIKE ?
                OR u.full_name LIKE ?
                OR p.project_status LIKE ?
            )
        """

        keyword_value = f"%{keyword}%"

        params.extend([
            keyword_value,
            keyword_value,
            keyword_value,
            keyword_value,
            keyword_value
        ])

    # ======================================================
    # Manager
    # ======================================================

    if manager != "All Managers":

        query += """
            AND u.full_name = ?
        """

        params.append(manager)

    # ======================================================
    # Status
    # ======================================================

    if status != "All Status":

        query += """
            AND p.project_status = ?
        """

        params.append(status)

    # ======================================================
    # Date Range Filter
    #
    # Project must overlap selected date range.
    #
    # Example:
    #
    # Project:
    #     2026-04-01 → 2026-08-20
    #
    # Selected:
    #     2026-06-01 → 2026-06-30
    #
    # Result:
    #     Project is shown because the ranges overlap.
    # ======================================================

    if date_start and date_end:

        query += """
            AND (
                p.start_date IS NULL
                OR p.start_date <= ?
            )

            AND (
                p.end_date IS NULL
                OR p.end_date >= ?
            )
        """

        params.extend([
            date_end,
            date_start
        ])

    # ======================================================
    # Order
    # ======================================================

    query += """
        ORDER BY p.id DESC
    """

    cursor.execute(
        query,
        params
    )

    result = cursor.fetchall()

    connection.close()

    return result


# ==========================================================
# Get Roadmap Projects
# ==========================================================

def get_roadmap_projects():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            project_code,
            project_name

        FROM projects

        ORDER BY id DESC
    """)

    result = cursor.fetchall()

    connection.close()

    return result


# ==========================================================
# Get Project Statuses
# ==========================================================

def get_project_statuses():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT DISTINCT
            project_status

        FROM projects

        WHERE project_status IS NOT NULL
          AND project_status != ''

        ORDER BY project_status
    """)

    result = cursor.fetchall()

    connection.close()

    return result


# ==========================================================
# Get Roadmap Project Dates
# ==========================================================

def get_roadmap_project_dates(project_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            start_date,
            end_date

        FROM projects

        WHERE id = ?
    """, (project_id,))

    result = cursor.fetchone()

    connection.close()

    return result


# ==========================================================
# Get Roadmap Project Expected Price
# ==========================================================

def get_roadmap_project_price(project_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            COALESCE(expected_price, 0)

        FROM projects

        WHERE id = ?
    """, (project_id,))

    result = cursor.fetchone()

    connection.close()

    if result:
        return result[0]

    return 0


# ==========================================================
# Get Roadmap Project Actual Price
# ==========================================================

def get_roadmap_project_actual_price(project_id):

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
# Create Project + Phases  (ATOMIC - one transaction)
# ==========================================================

class DuplicateProjectCodeError(Exception):
    """Raised when project_code already exists (UNIQUE constraint)."""
    pass


def create_project_with_phases(project_data, phases):
    """
    project_data: dict of the columns accepted by insert_project()
    phases: list of (phase_id, percentage, start_date, end_date)

    Inserts the project AND every phase in a single transaction:
    either all of it lands in the database, or none of it does - a
    phase insert failing can never leave a project with no phases.
    """

    try:

        with connect() as connection:

            cursor = connection.cursor()

            cursor.execute("""
                INSERT INTO projects(
                    project_code, project_name, client_id, project_type,
                    department_id, manager_id, start_date, end_date,
                    priority, project_status, description, expected_price
                )
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                project_data["project_code"],
                project_data["project_name"],
                project_data.get("client_id"),
                project_data.get("project_type"),
                project_data.get("department_id"),
                project_data.get("manager_id"),
                project_data.get("start_date"),
                project_data.get("end_date"),
                project_data.get("priority", "Medium"),
                project_data.get("project_status", "Open"),
                project_data.get("description"),
                project_data.get("expected_price", 0),
            ))

            project_id = cursor.lastrowid

            for phase_id, percentage, start_date, end_date in phases:

                cursor.execute("""
                    INSERT INTO project_phases(
                        project_id, phase_id, percentage, start_date, end_date
                    )
                    VALUES(?,?,?,?,?)
                """, (project_id, phase_id, percentage, start_date, end_date))

            return project_id

    except sqlite3.IntegrityError as error:

        if "project_code" in str(error).lower():
            raise DuplicateProjectCodeError(
                f"Project code '{project_data['project_code']}' is "
                "already in use."
            ) from error

        raise


# ==========================================================
# Update Project + Phases  (ATOMIC - one transaction)
# ==========================================================

def update_project_with_phases(project_id, project_data, phases,
                                deleted_phase_ids=()):
    """
    Same idea as create_project_with_phases(): updates the project row,
    updates/inserts every given phase, and deletes any phase the user
    removed in the UI - all inside ONE transaction.

    phases: list of (project_phase_id_or_None, phase_id, percentage,
                      progress, start_date, end_date, expected_price)
            project_phase_id is None for a phase that is being added.
    """

    try:

        with connect() as connection:

            cursor = connection.cursor()

            cursor.execute("""
                UPDATE projects
                SET
                    project_code = ?, project_name = ?, client_id = ?,
                    project_type = ?, department_id = ?, manager_id = ?,
                    start_date = ?, end_date = ?, priority = ?,
                    project_status = ?, description = ?, expected_price = ?
                WHERE id = ?
            """, (
                project_data["project_code"],
                project_data["project_name"],
                project_data.get("client_id"),
                project_data.get("project_type"),
                project_data.get("department_id"),
                project_data.get("manager_id"),
                project_data.get("start_date"),
                project_data.get("end_date"),
                project_data.get("priority"),
                project_data.get("project_status"),
                project_data.get("description"),
                project_data.get("expected_price", 0),
                project_id,
            ))

            for phase_row in phases:

                (project_phase_id, phase_id, percentage, progress,
                 start_date, end_date, expected_price) = phase_row

                if project_phase_id is None:

                    cursor.execute("""
                        INSERT INTO project_phases(
                            project_id, phase_id, percentage, progress,
                            start_date, end_date, expected_price
                        )
                        VALUES(?,?,?,?,?,?,?)
                    """, (project_id, phase_id, percentage, progress,
                          start_date, end_date, expected_price))

                else:

                    cursor.execute("""
                        UPDATE project_phases
                        SET percentage = ?, progress = ?, start_date = ?,
                            end_date = ?, expected_price = ?
                        WHERE id = ? AND project_id = ?
                    """, (percentage, progress, start_date, end_date,
                          expected_price, project_phase_id, project_id))

            for project_phase_id in deleted_phase_ids:

                cursor.execute(
                    "DELETE FROM project_phases WHERE id = ? AND project_id = ?",
                    (project_phase_id, project_id)
                )

    except sqlite3.IntegrityError as error:

        if "project_code" in str(error).lower():
            raise DuplicateProjectCodeError(
                f"Project code '{project_data['project_code']}' is "
                "already in use."
            ) from error

        raise
