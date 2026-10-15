from db.connection import get_connection
from db.migrations import init_database
from db.lookups import (
    CATEGORIES,
    ENTITIES,
    get_values,
    get_lookup_rows,
    usage_count,
    add_value,
    rename_value,
    set_active,
    delete_value,
    move_value,
    get_entity_rows,
    save_entity,
    entity_usage,
)
from db.history import (
    ENTITY_TITLES,
    get_history,
    get_history_count,
    get_data_version,
    clear_history,
    describe_changes,
    set_session_user,
)
from db.permissions import (
    PERMISSIONS,
    ALL_PERMISSIONS,
    SYSTEM_ROLES,
    has_permission,
    get_permissions_for_role,
    list_roles,
    role_user_count,
    create_role,
    rename_role,
    delete_role,
    set_role_permissions,
)


# =========================================================
# PROJECTS
# =========================================================

from db.projects import (
    insert_project,
    generate_project_code,
    get_project_by_code,
    get_project_details,
    update_project,
    get_projects,
    remove_project,
    get_managers,
    get_project_statuses,
    search_projects,
    get_roadmap_projects,
    get_roadmap_project_price,
    get_roadmap_project_actual_price,

    get_roadmap_project_dates,

    create_project_with_phases,
    update_project_with_phases,
    DuplicateProjectCodeError,
)




# =========================================================
# PHASES
# =========================================================

from db.phases import (
    get_phases,
    insert_phase,
    update_phase,
    delete_phase,
    get_phase_id,
    get_project_phases,
    insert_project_phase,
    update_project_phase,
    get_roadmap_phases,
    get_roadmap_overall,
    get_roadmap_overall_actual,
)


# =========================================================
# EXPENSES
# =========================================================

from db.expenses import (
    create_expenses_table,
    migrate_expenses_table,
    insert_expense,
    get_expenses,
    search_expenses,
    get_expense_by_id,
    update_expense,
    delete_expense,
    get_expense_total,
    get_phase_actual_price,
    get_expense_phases,
    get_expense_projects,
)


# =========================================================
# CONTRACTS
# =========================================================


from db.contracts import (
    get_contracts,
    get_contract_by_id,
    insert_contract,
    update_contract,
    get_contract_statuses,
    delete_contract,
    get_contract_projects,
    search_contracts,
)



# =========================================================
# ARCHIVE
# =========================================================

from db.archive import (
    create_archive_table,
    archive_record,
    archive_cascade,
    archive_single_record,
    get_archived_records,
    get_archive_event,
    restore_archive_event,
    permanently_delete_archive_event,
)


# =========================================================
# LOOKUPS
# =========================================================

def get_clients():
    """
    Get all clients.
    """

    connection = get_connection()

    try:
        return connection.execute("""
            SELECT id, company_name
            FROM clients
            ORDER BY company_name
        """).fetchall()

    finally:
        connection.close()


def get_departments():
    """
    Get all departments.
    """

    connection = get_connection()

    try:
        return connection.execute("""
            SELECT id, department_name
            FROM departments
            ORDER BY department_name
        """).fetchall()

    finally:
        connection.close()


# =========================================================
# DATABASE INITIALIZATION  (call once at start-up from main.py)
# =========================================================

def setup_database():
    init_database()
    create_archive_table()
    create_expenses_table()
    migrate_expenses_table()