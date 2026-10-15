from .connection import get_connection, validate_progress
from .permissions import require_session_permission


# ==========================================================
# Get All Phases
# ==========================================================

def get_phases():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            phase_name
        FROM phases
        WHERE is_active = 1
        ORDER BY id
    """)

    result = cursor.fetchall()

    connection.close()

    return result


# ==========================================================
# Insert Phase
# ==========================================================

def insert_phase(phase_name):

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO phases(
                phase_name
            )
            VALUES(?)
        """, (phase_name,))

        connection.commit()

    finally:
        connection.close()


# ==========================================================
# Update Phase
# ==========================================================

def update_phase(
    phase_id,
    phase_name
):

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE phases

            SET phase_name = ?

            WHERE id = ?
        """, (
            phase_name,
            phase_id
        ))

        connection.commit()

    finally:
        connection.close()


# ==========================================================
# Delete Phase
# ==========================================================

def delete_phase(phase_id):

    connection = get_connection()

    try:
        require_session_permission(connection, "projects.delete")
    except Exception:
        connection.close()
        raise

    cursor = connection.cursor()

    usage = cursor.execute(
        "SELECT COUNT(*) FROM project_phases WHERE phase_id = ?", (phase_id,)
    ).fetchone()[0]
    if usage:
        connection.close()
        raise ValueError(
            "This phase is used by one or more projects. Reassign or remove those "
            "phase entries before deleting the phase definition."
        )

    cursor.execute("""
        DELETE FROM phases

        WHERE id = ?
    """, (phase_id,))

    connection.commit()

    connection.close()


# ==========================================================
# Get Phase ID By Name
# ==========================================================

def get_phase_id(phase_name):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id
        FROM phases
        WHERE phase_name = ?
    """, (phase_name,))

    result = cursor.fetchone()

    connection.close()

    if result:
        return result[0]

    return None


# ==========================================================
# Get Project Phases
# ==========================================================
def get_project_phases(project_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            project_phases.id,
            phases.phase_name,
            project_phases.percentage,
            project_phases.progress,
            project_phases.start_date,
            project_phases.end_date,
            COALESCE(project_phases.expected_price, 0)

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
# Insert Project Phase
# ==========================================================

def insert_project_phase(
    project_id,
    phase_id,
    percentage,
    start_date=None,
    end_date=None
):

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO project_phases(
                project_id,
                phase_id,
                percentage,
                start_date,
                end_date
            )
            VALUES(?,?,?,?,?)
        """, (
            project_id,
            phase_id,
            percentage,
            start_date,
            end_date
        ))

        connection.commit()

    finally:
        connection.close()


# ==========================================================
# Update Project Phase
# ==========================================================

def update_project_phase(
    project_phase_id,
    percentage,
    progress,
    start_date=None,
    end_date=None,
    expected_price=0
):
    validate_progress(progress)

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE project_phases

            SET
                percentage = ?,
                progress = ?,
                start_date = ?,
                end_date = ?,
                expected_price = ?

            WHERE id = ?
        """, (
            percentage,
            progress,
            start_date,
            end_date,
            expected_price,
            project_phase_id
        ))

        connection.commit()

    finally:
        connection.close()

# ==========================================================
# Get Roadmap Phases
# ==========================================================

def get_roadmap_phases(project_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            project_phases.id,
            phases.phase_name,
            project_phases.percentage,
            project_phases.progress,
            project_phases.status,
            project_phases.start_date,
            project_phases.end_date,
            COALESCE(project_phases.expected_price, 0)

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
# Get Roadmap Overall
# ==========================================================

def get_roadmap_overall(project_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT

            COALESCE(SUM(percentage), 0),

            COALESCE(
                SUM(
                    percentage * progress / 100.0
                ),
                0
            )

        FROM project_phases

        WHERE project_id = ?
          AND status NOT IN ('Skipped', 'Cancelled')
    """, (project_id,))

    result = cursor.fetchone()

    connection.close()

    if not result:
        return 0, 0

    total_percentage = result[0]

    actual_weighted = result[1]

    if total_percentage == 0:
        return 0, 0

    expected = total_percentage

    actual = (
        actual_weighted /
        total_percentage
    ) * 100

    return actual, expected


# ==========================================================
# Get Roadmap Overall Actual
# ==========================================================

def get_roadmap_overall_actual(project_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT

            COALESCE(
                SUM(
                    percentage * progress
                ),
                0
            ),

            COALESCE(
                SUM(percentage),
                0
            )

        FROM project_phases

        WHERE project_id = ?
          AND status NOT IN ('Skipped', 'Cancelled')
    """, (project_id,))

    result = cursor.fetchone()

    connection.close()

    if not result or result[1] == 0:
        return 0

    weighted_progress = result[0]

    total_weight = result[1]

    return weighted_progress / total_weight