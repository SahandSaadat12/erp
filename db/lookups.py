"""
Editable lists (statuses, types, priorities, categories ...) + simple
entities (clients, managers, departments, phases) managed from
Settings -> Lists.

Lookup values live in the `lookups` table.  Values that program logic
depends on (e.g. project status "Completed") are flagged is_system and
cannot be renamed / deleted - you can still ADD new ones next to them.
"""

import sqlite3

from .connection import connect, get_connection


# ----------------------------------------------------------------------
# Lookup categories
#   key -> (title, [(table, column), ...] where the value is stored,
#           default values,  system (protected) values)
# ----------------------------------------------------------------------

CATEGORIES = {

    "project_status": (
        "Project Status",
        [("projects", "project_status")],
        ["Open", "In Progress", "On Hold", "Completed", "Cancelled", "Closed"],
        ["Open", "In Progress", "Completed"],
    ),

    "project_type": (
        "Project Type",
        [("projects", "project_type")],
        ["Fabrication", "Production", "Installation", "Maintenance",
         "Repair", "Engineering", "Other"],
        [],
    ),

    "priority": (
        "Priority",
        [("projects", "priority"), ("tasks", "priority")],
        ["Low", "Medium", "High", "Critical"],
        [],
    ),

    "phase_status": (
        "Phase Status",
        [("project_phases", "status")],
        ["Pending", "In Progress", "Completed", "Skipped", "Cancelled"],
        ["Pending", "In Progress", "Completed", "Skipped", "Cancelled"],
    ),

    "contract_status": (
        "Contract Status",
        [("contracts", "status")],
        ["Active", "Completed", "Canceled"],
        [],
    ),

    "expense_status": (
        "Expense Status",
        [("expenses", "status")],
        ["Pending", "Paid", "Cancelled"],
        [],
    ),

    "expense_category": (
        "Expense Category",
        [("expenses", "category")],
        ["Materials", "Transport", "Equipment", "Salary",
         "Office", "Software", "Other"],
        [],
    ),

    "document_type": (
        "Document Type",
        [("documents", "document_type")],
        ["Contract", "Invoice", "Report", "Other"],
        [],
    ),
}


# ----------------------------------------------------------------------
# Entities  (real tables)
#   key -> (title, table, id, [(column, label, required)], display column,
#           extra info)
# ----------------------------------------------------------------------

ENTITIES = {

    "clients": (
        "Clients", "clients", "company_name",
        [("company_name", "Company Name", True),
         ("contact_person", "Contact Person", False),
         ("phone", "Phone", False),
         ("email", "Email", False),
         ("address", "Address", False)],
    ),

    "managers": (
        "Managers / Users", "users", "full_name",
        [("full_name", "Full Name", True),
         ("username", "Username", True),
         ("password", "New Password (leave empty to keep current)", False),
         ("role", "Role", True),
         ("status", "Status (Active / Inactive)", False)],
    ),

    "departments": (
        "Departments", "departments", "department_name",
        [("department_name", "Department Name", True)],
    ),

    "phases": (
        "Phases", "phases", "phase_name",
        [("phase_name", "Phase Name", True),
         ("is_active", "Active (1 / 0)", False)],
    ),
}


# ----------------------------------------------------------------------
# Seeding / reading
# ----------------------------------------------------------------------

def seed_lookups(connection):
    """Defaults + every value already used by existing records."""

    for category, (title, usage, defaults, system) in CATEGORIES.items():

        existing = connection.execute(
            "SELECT COUNT(*) FROM lookups WHERE category = ?", (category,)
        ).fetchone()[0]

        if existing:
            continue

        order = 0
        seen = set()

        for value in defaults:
            connection.execute(
                """INSERT OR IGNORE INTO lookups
                   (category, value, sort_order, is_system, is_active)
                   VALUES (?, ?, ?, ?, 1)""",
                (category, value, order, 1 if value in system else 0)
            )
            seen.add(value)
            order += 1

        # values that already exist in the data must stay selectable
        for table, column in usage:
            try:
                rows = connection.execute(
                    f'SELECT DISTINCT "{column}" FROM "{table}" '
                    f'WHERE "{column}" IS NOT NULL AND TRIM("{column}") <> ""'
                ).fetchall()
            except Exception:
                continue

            for (value,) in rows:
                if value not in seen:
                    connection.execute(
                        """INSERT OR IGNORE INTO lookups
                           (category, value, sort_order, is_system, is_active)
                           VALUES (?, ?, ?, 0, 1)""",
                        (category, value, order)
                    )
                    seen.add(value)
                    order += 1


def get_values(category, include_inactive=False):
    """Plain list of strings for a combobox."""

    connection = get_connection()

    try:
        sql = "SELECT value FROM lookups WHERE category = ?"

        if not include_inactive:
            sql += " AND is_active = 1"

        sql += " ORDER BY sort_order, id"

        values = [r[0] for r in connection.execute(sql, (category,))]

    finally:
        connection.close()

    if not values and category in CATEGORIES:
        return list(CATEGORIES[category][2])

    return values


def get_lookup_rows(category):
    connection = get_connection()

    try:
        return connection.execute(
            """SELECT id, value, sort_order, is_system, is_active
               FROM lookups WHERE category = ?
               ORDER BY sort_order, id""",
            (category,)
        ).fetchall()
    finally:
        connection.close()


def usage_count(category, value):
    """How many records currently use this value."""

    connection = get_connection()

    try:
        total = 0

        for table, column in CATEGORIES[category][1]:
            total += connection.execute(
                f'SELECT COUNT(*) FROM "{table}" WHERE "{column}" = ?',
                (value,)
            ).fetchone()[0]

        return total

    finally:
        connection.close()


# ----------------------------------------------------------------------
# Lookup CRUD
# ----------------------------------------------------------------------

def add_value(category, value):

    value = (value or "").strip()

    if not value:
        raise ValueError("Value cannot be empty.")

    with connect() as connection:

        exists = connection.execute(
            "SELECT 1 FROM lookups WHERE category = ? AND LOWER(value) = LOWER(?)",
            (category, value)
        ).fetchone()

        if exists:
            raise ValueError(f"'{value}' already exists.")

        order = connection.execute(
            "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM lookups WHERE category = ?",
            (category,)
        ).fetchone()[0]

        connection.execute(
            """INSERT INTO lookups(category, value, sort_order, is_system, is_active)
               VALUES (?, ?, ?, 0, 1)""",
            (category, value, order)
        )


def rename_value(lookup_id, new_value):
    """Renames the value AND every record that uses it."""

    new_value = (new_value or "").strip()

    if not new_value:
        raise ValueError("Value cannot be empty.")

    with connect() as connection:

        row = connection.execute(
            "SELECT category, value, is_system FROM lookups WHERE id = ?",
            (lookup_id,)
        ).fetchone()

        if row is None:
            raise ValueError("Item not found.")

        category, old_value, is_system = row

        if is_system:
            raise ValueError(
                f"'{old_value}' is used by the program logic and cannot "
                "be renamed."
            )

        if new_value == old_value:
            return

        clash = connection.execute(
            """SELECT 1 FROM lookups
               WHERE category = ? AND LOWER(value) = LOWER(?) AND id <> ?""",
            (category, new_value, lookup_id)
        ).fetchone()

        if clash:
            raise ValueError(f"'{new_value}' already exists.")

        connection.execute(
            "UPDATE lookups SET value = ? WHERE id = ?",
            (new_value, lookup_id)
        )

        for table, column in CATEGORIES[category][1]:
            connection.execute(
                f'UPDATE "{table}" SET "{column}" = ? WHERE "{column}" = ?',
                (new_value, old_value)
            )


def set_active(lookup_id, active):

    with connect() as connection:

        row = connection.execute(
            "SELECT value, is_system FROM lookups WHERE id = ?",
            (lookup_id,)
        ).fetchone()

        if row is None:
            raise ValueError("Item not found.")

        if row[1] and not active:
            raise ValueError(
                f"'{row[0]}' is used by the program logic and cannot be hidden."
            )

        connection.execute(
            "UPDATE lookups SET is_active = ? WHERE id = ?",
            (1 if active else 0, lookup_id)
        )


def delete_value(lookup_id):
    """Refuses system values and values still used by records."""

    with connect() as connection:

        row = connection.execute(
            "SELECT category, value, is_system FROM lookups WHERE id = ?",
            (lookup_id,)
        ).fetchone()

        if row is None:
            raise ValueError("Item not found.")

        category, value, is_system = row

        if is_system:
            raise ValueError(
                f"'{value}' is used by the program logic and cannot be deleted."
            )

        used = 0

        for table, column in CATEGORIES[category][1]:
            used += connection.execute(
                f'SELECT COUNT(*) FROM "{table}" WHERE "{column}" = ?',
                (value,)
            ).fetchone()[0]

        if used:
            raise ValueError(
                f"'{value}' is used by {used} record(s).\n\n"
                "Rename it, or hide it so it no longer appears in new forms."
            )

        connection.execute("DELETE FROM lookups WHERE id = ?", (lookup_id,))


def move_value(lookup_id, direction):
    """direction = -1 (up) / +1 (down)."""

    with connect() as connection:

        row = connection.execute(
            "SELECT category FROM lookups WHERE id = ?", (lookup_id,)
        ).fetchone()

        if row is None:
            return

        ids = [
            r[0] for r in connection.execute(
                "SELECT id FROM lookups WHERE category = ? ORDER BY sort_order, id",
                (row[0],)
            )
        ]

        index = ids.index(lookup_id)
        target = index + direction

        if target < 0 or target >= len(ids):
            return

        ids[index], ids[target] = ids[target], ids[index]

        for order, item_id in enumerate(ids):
            connection.execute(
                "UPDATE lookups SET sort_order = ? WHERE id = ?",
                (order, item_id)
            )


# ----------------------------------------------------------------------
# Entities (clients / managers / departments / phases)
# ----------------------------------------------------------------------

def get_entity_rows(key):

    title, table, display, fields = ENTITIES[key]

    columns = ", ".join(f'"{c}"' for c, _, _ in fields)

    connection = get_connection()

    try:
        return connection.execute(
            f'SELECT id, {columns} FROM "{table}" ORDER BY "{display}"'
        ).fetchall()
    finally:
        connection.close()


def save_entity(key, record_id, values, current_user=None):
    """record_id None -> insert, otherwise update.  values = {column: text}.

    User account changes require users.manage; ordinary lists require
    settings.manage/clients.manage as appropriate. Callers must pass the
    authenticated current_user rather than relying only on disabled UI.
    """
    from .permissions import has_permission
    required_permission = "users.manage" if key == "managers" else (
        "clients.manage" if key == "clients" else "settings.manage"
    )
    if not has_permission(current_user, required_permission):
        raise PermissionError(f"Missing permission: {required_permission}")

    title, table, display, fields = ENTITIES[key]

    clean = {}

    for column, label, required in fields:

        value = (values.get(column) or "").strip()

        if required and not value:
            raise ValueError(f"'{label}' is required.")

        clean[column] = value if value != "" else None

    if key == "phases":
        clean["is_active"] = 0 if str(clean.get("is_active") or "1") in ("0", "No", "no") else 1

    if key == "managers":

        clean["status"] = clean.get("status") or "Active"

        from security import hash_password

        new_password = clean.get("password")

        if new_password:
            clean["password"] = hash_password(new_password)
        else:
            clean.pop("password", None)   # left empty -> keep existing password

        if record_id is None and "password" not in clean:
            raise ValueError("A password is required for a new user.")

    try:

        with connect() as connection:
            from .permissions import require_session_permission
            require_session_permission(connection, required_permission)

            if record_id is None:

                columns = list(clean)

                connection.execute(
                    f'INSERT INTO "{table}" '
                    f'({", ".join(chr(34) + c + chr(34) for c in columns)}) '
                    f'VALUES ({", ".join("?" for _ in columns)})',
                    [clean[c] for c in columns]
                )

            else:

                columns = list(clean)

                connection.execute(
                    f'UPDATE "{table}" SET '
                    f'{", ".join(chr(34) + c + chr(34) + " = ?" for c in columns)} '
                    f'WHERE id = ?',
                    [clean[c] for c in columns] + [record_id]
                )

    except sqlite3.IntegrityError as error:

        if key == "managers" and "username" in str(error).lower():
            username = clean.get("username")
            raise ValueError(
                f"Username '{username}' is already taken "
                "(usernames are not case-sensitive)."
            ) from error

        raise ValueError(
            f"'{clean.get(display)}' already exists."
        ) from error


def entity_usage(key, record_id):
    """Number of records that point at this entity (for the delete warning)."""

    refs = {
        "clients": [("projects", "client_id"), ("contracts", "client_id")],
        "managers": [("projects", "manager_id")],
        "departments": [("projects", "department_id")],
        "phases": [("project_phases", "phase_id"), ("projects", "current_phase_id")],
    }[key]

    connection = get_connection()

    try:
        return sum(
            connection.execute(
                f'SELECT COUNT(*) FROM "{t}" WHERE "{c}" = ?', (record_id,)
            ).fetchone()[0]
            for t, c in refs
        )
    finally:
        connection.close()
