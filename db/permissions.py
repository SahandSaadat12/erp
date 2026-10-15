"""
Real RBAC (role-based access control).

Roles live in the `roles` table; what each role can do lives in
`role_permissions` (role_id, permission).  users.role stays a plain
TEXT column (so existing data / the Managers list UI don't need to
change) but it must match a name in `roles` for permissions to apply -
an unknown role name simply has zero permissions, which is the safe
default (fail closed, not fail open).

has_permission() is the ONLY function the rest of the app should call
to decide whether an action is allowed - UI code uses it to
enable/disable buttons, and the db/*.py functions that perform
sensitive actions (delete, clear history, permanent delete, ...) call
it again themselves, so a permission can never be bypassed by skipping
the UI (see delete_project() in db/projects_actions.py for the
pattern).
"""

from .connection import connect, get_connection


# ----------------------------------------------------------------------
# Permission catalog - grouped only for the Settings UI; the string on
# the left is what has_permission() checks and what the database stores.
# ----------------------------------------------------------------------

PERMISSIONS = {
    "Projects": [
        ("projects.view", "View"),
        ("projects.create", "Create"),
        ("projects.edit", "Edit"),
        ("projects.delete", "Delete / Archive"),
        ("projects.restore", "Restore"),
    ],
    "Contracts": [
        ("contracts.view", "View"),
        ("contracts.create", "Create"),
        ("contracts.edit", "Edit"),
        ("contracts.delete", "Delete / Archive"),
        ("contracts.restore", "Restore"),
    ],
    "Expenses": [
        ("expenses.view", "View"),
        ("expenses.create", "Create"),
        ("expenses.edit", "Edit"),
        ("expenses.delete", "Delete / Archive"),
        ("expenses.restore", "Restore"),
    ],
    "Documents": [
        ("documents.view", "View"),
        ("documents.create", "Create"),
        ("documents.edit", "Edit"),
        ("documents.delete", "Delete / Archive"),
        ("documents.restore", "Restore"),
    ],
    "Roadmap": [
        ("roadmap.view", "View"),
        ("roadmap.edit", "Edit"),
    ],
    "Clients": [
        ("clients.view", "View"),
        ("clients.manage", "Create / Edit / Delete"),
    ],
    "Users & Roles": [
        ("users.manage", "Manage Users"),
        ("roles.manage", "Manage Roles & Permissions"),
    ],
    "Settings": [
        ("settings.view", "Open Settings"),
        ("settings.manage", "Manage Lists"),
    ],
    "History & Archive": [
        ("history.view", "View History"),
        ("history.clear", "Clear History"),
        ("archive.view", "View Archive"),
        ("archive.restore", "Restore from Archive"),
        ("archive.permanent_delete", "Delete Forever"),
    ],
    "Backup": [
        ("backup.create", "Create Backup"),
        ("backup.restore", "Restore Backup"),
    ],
}

ALL_PERMISSIONS = [key for group in PERMISSIONS.values() for key, _ in group]

# seeded once, on a brand-new database - afterwards the user can edit
# everything from Settings -> Roles & Permissions
DEFAULT_ROLES = {
    "Manager": ALL_PERMISSIONS,                      # full access
    "Supervisor": [
        "projects.view", "projects.create", "projects.edit",
        "contracts.view", "contracts.create", "contracts.edit",
        "expenses.view", "expenses.create", "expenses.edit",
        "documents.view", "documents.create", "documents.edit",
        "roadmap.view", "roadmap.edit", "clients.view",
        "history.view", "archive.view", "settings.view",
    ],
    "Engineer": [
        "projects.view", "contracts.view", "expenses.view",
        "documents.view", "documents.create",
        "roadmap.view", "roadmap.edit", "clients.view",
    ],
    "QC": [
        "projects.view", "documents.view", "documents.create",
        "roadmap.view", "clients.view",
    ],
}

SYSTEM_ROLES = {"Manager"}      # cannot be deleted / stripped of users.manage


# ----------------------------------------------------------------------
# Seeding (called from db/migrations.py)
# ----------------------------------------------------------------------

def seed_roles(connection):

    existing = {
        row[0] for row in connection.execute("SELECT name FROM roles")
    }

    # roles referenced by existing users but missing from the table
    used_roles = {
        row[0] for row in connection.execute(
            "SELECT DISTINCT role FROM users WHERE role IS NOT NULL AND role <> ''"
        )
    }

    for name in set(DEFAULT_ROLES) | used_roles:

        if name in existing:
            # Add newly introduced system permissions without resetting a
            # customer's existing role customizations.
            if name.casefold() == "manager":
                role_id = connection.execute(
                    "SELECT id FROM roles WHERE name = ? COLLATE NOCASE", (name,)
                ).fetchone()[0]
                connection.execute(
                    "INSERT OR IGNORE INTO role_permissions(role_id, permission) VALUES (?, ?)",
                    (role_id, "backup.restore"),
                )
            continue

        connection.execute(
            "INSERT INTO roles(name, is_system) VALUES (?, ?)",
            (name, 1 if name in SYSTEM_ROLES else 0)
        )

        role_id = connection.execute(
            "SELECT id FROM roles WHERE name = ?", (name,)
        ).fetchone()[0]

        for permission in DEFAULT_ROLES.get(name, []):
            connection.execute(
                "INSERT OR IGNORE INTO role_permissions(role_id, permission) "
                "VALUES (?, ?)",
                (role_id, permission)
            )

    connection.execute(
        "INSERT OR IGNORE INTO session_context(id, user_id, username) "
        "VALUES (1, NULL, NULL)"
    )


# ----------------------------------------------------------------------
# Reading
# ----------------------------------------------------------------------

def get_permissions_for_role(role_name):

    if not role_name:
        return set()

    connection = get_connection()

    try:
        row = connection.execute(
            "SELECT id FROM roles WHERE name = ? COLLATE NOCASE", (role_name,)
        ).fetchone()

        if row is None:
            return set()

        rows = connection.execute(
            "SELECT permission FROM role_permissions WHERE role_id = ?",
            (row[0],)
        ).fetchall()

        return {r[0] for r in rows}

    finally:
        connection.close()


def has_permission(current_user, permission):
    """
    current_user: the dict stored by the login screen - must contain
    "permissions" (a set/list of permission strings).  Works safely even
    if current_user is None or malformed: no permissions -> denied.
    """

    if not current_user:
        return False

    return permission in (current_user.get("permissions") or ())


def list_roles():

    connection = get_connection()

    try:
        return connection.execute(
            "SELECT id, name, is_system FROM roles ORDER BY name"
        ).fetchall()

    finally:
        connection.close()


def role_user_count(role_name):

    connection = get_connection()

    try:
        return connection.execute(
            "SELECT COUNT(*) FROM users WHERE role = ? COLLATE NOCASE",
            (role_name,)
        ).fetchone()[0]

    finally:
        connection.close()


# ----------------------------------------------------------------------
# Writing
# ----------------------------------------------------------------------

def create_role(name):

    name = (name or "").strip()

    if not name:
        raise ValueError("Role name is required.")

    with connect() as connection:

        exists = connection.execute(
            "SELECT 1 FROM roles WHERE name = ? COLLATE NOCASE", (name,)
        ).fetchone()

        if exists:
            raise ValueError(f"Role '{name}' already exists.")

        connection.execute(
            "INSERT INTO roles(name, is_system) VALUES (?, 0)", (name,)
        )


def rename_role(role_id, new_name):

    new_name = (new_name or "").strip()

    if not new_name:
        raise ValueError("Role name is required.")

    with connect() as connection:

        row = connection.execute(
            "SELECT name, is_system FROM roles WHERE id = ?", (role_id,)
        ).fetchone()

        if row is None:
            raise ValueError("Role not found.")

        old_name, is_system = row

        if is_system:
            raise ValueError(f"'{old_name}' is a built-in role and can't be renamed.")

        clash = connection.execute(
            "SELECT 1 FROM roles WHERE name = ? COLLATE NOCASE AND id <> ?",
            (new_name, role_id)
        ).fetchone()

        if clash:
            raise ValueError(f"Role '{new_name}' already exists.")

        connection.execute("UPDATE roles SET name = ? WHERE id = ?", (new_name, role_id))
        connection.execute(
            "UPDATE users SET role = ? WHERE role = ? COLLATE NOCASE",
            (new_name, old_name)
        )


def delete_role(role_id):

    with connect() as connection:

        row = connection.execute(
            "SELECT name, is_system FROM roles WHERE id = ?", (role_id,)
        ).fetchone()

        if row is None:
            raise ValueError("Role not found.")

        name, is_system = row

        if is_system:
            raise ValueError(f"'{name}' is a built-in role and can't be deleted.")

        in_use = connection.execute(
            "SELECT COUNT(*) FROM users WHERE role = ? COLLATE NOCASE", (name,)
        ).fetchone()[0]

        if in_use:
            raise ValueError(
                f"'{name}' is assigned to {in_use} user(s). "
                "Reassign them to another role first."
            )

        connection.execute("DELETE FROM role_permissions WHERE role_id = ?", (role_id,))
        connection.execute("DELETE FROM roles WHERE id = ?", (role_id,))


def set_role_permissions(role_id, permissions):
    """permissions: iterable of permission-key strings to grant (replaces the set)."""

    with connect() as connection:

        row = connection.execute(
            "SELECT name, is_system FROM roles WHERE id = ?", (role_id,)
        ).fetchone()

        if row is None:
            raise ValueError("Role not found.")

        name, is_system = row

        wanted = set(permissions) & set(ALL_PERMISSIONS)

        if is_system:
            # built-in Manager role must always keep full access, so the
            # app can never be locked out of its own Settings/Roles screen
            wanted |= set(ALL_PERMISSIONS)

        connection.execute("DELETE FROM role_permissions WHERE role_id = ?", (role_id,))

        connection.executemany(
            "INSERT INTO role_permissions(role_id, permission) VALUES (?, ?)",
            [(role_id, permission) for permission in wanted]
        )


def require_session_permission(connection, permission):
    """Raise PermissionError unless the currently logged-in DB session has permission.

    This is a second line of defence for sensitive database operations; UI
    button visibility is not treated as authorization. This application is
    single-user/single-session and must not be deployed as multi-user yet.
    """
    row = connection.execute(
        "SELECT user_id FROM session_context WHERE id = 1"
    ).fetchone()
    if not row or row[0] is None:
        raise PermissionError("An authenticated user session is required.")
    user = connection.execute(
        "SELECT role, status FROM users WHERE id = ?", (row[0],)
    ).fetchone()
    if not user or (user[1] or "Active") != "Active":
        raise PermissionError("The user account is missing or disabled.")
    allowed = connection.execute(
        """SELECT 1 FROM roles r
           JOIN role_permissions rp ON rp.role_id = r.id
           WHERE r.name = ? COLLATE NOCASE AND rp.permission = ? LIMIT 1""",
        (user[0], permission),
    ).fetchone()
    if not allowed:
        raise PermissionError(f"Missing permission: {permission}")
    return True
