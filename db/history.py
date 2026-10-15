"""
History / audit log.

Everything is recorded by SQLite TRIGGERS, so no screen has to remember
to log anything: every add, edit and delete on the tracked tables ends up
in the `history` table (with the old and new values as JSON).

* Deleting through the app moves the record to the Archive (see
  archive.py) - those events are logged by archive.py as "delete" /
  "restore" / "purge" and the row-by-row noise of cascades is muted via
  history_ctx.suppress.
* Settings -> History shows the log;  "Clear History" empties it.
"""

import json
from .permissions import require_session_permission

from .connection import connect, get_connection


# table -> (label SQL using {p} for NEW/OLD, label template for python,
#           is_parent (deleting it cascades / nulls children))
TRACKED = {
    "projects": ("{p}.project_code || ' - ' || {p}.project_name", True),
    "contracts": ("COALESCE({p}.contract_name, '')", False),
    "expenses": ("COALESCE({p}.title, {p}.category, '') || ' (' || COALESCE({p}.amount, 0) || ')'", False),
    "documents": ("COALESCE({p}.title, '')", False),
    "clients": ("{p}.company_name", True),
    "users": ("{p}.full_name", True),
    "departments": ("{p}.department_name", True),
    "phases": ("{p}.phase_name", True),
    "project_phases": (
        "COALESCE((SELECT project_code FROM projects WHERE id = {p}.project_id), '?')"
        " || ' / ' || COALESCE((SELECT phase_name FROM phases WHERE id = {p}.phase_id), '?')",
        False,
    ),
    "tasks": ("COALESCE({p}.title, '')", False),
    "lookups": ("{p}.category || ': ' || {p}.value", False),
}

NEVER_LOG_COLUMNS = {"password"}

ENTITY_TITLES = {
    "projects": "Project",
    "contracts": "Contract",
    "expenses": "Expense",
    "documents": "Document",
    "clients": "Client",
    "users": "Manager / User",
    "departments": "Department",
    "phases": "Phase",
    "project_phases": "Project Phase",
    "tasks": "Task",
    "lookups": "List Item",
}


# ----------------------------------------------------------------------
# Triggers
# ----------------------------------------------------------------------

def _json_expr(connection, table, prefix):

    columns = [
        row[1]
        for row in connection.execute(f'PRAGMA table_info("{table}")')
        if row[1] not in NEVER_LOG_COLUMNS
    ]

    parts = ", ".join(f"'{c}', {prefix}.\"{c}\"" for c in columns)

    return f"json_object({parts})"


def install_triggers(connection):

    muted = "(SELECT suppress FROM history_ctx WHERE id = 1) = 0"

    for table, (label, is_parent) in TRACKED.items():

        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,)
        ).fetchone()

        if not exists:
            continue

        new_json = _json_expr(connection, table, "NEW")
        old_json = _json_expr(connection, table, "OLD")

        new_label = label.format(p="NEW")
        old_label = label.format(p="OLD")

        for suffix in ("ai", "au", "ad", "bd"):
            connection.execute(f"DROP TRIGGER IF EXISTS trg_hist_{table}_{suffix}")

        connection.execute(f"""
            CREATE TRIGGER trg_hist_{table}_ai AFTER INSERT ON "{table}"
            WHEN {muted}
            BEGIN
                INSERT INTO history(
                    action, entity, entity_id, label, new_data,
                    performed_by_user_id, performed_by_username
                )
                VALUES (
                    COALESCE((SELECT action FROM history_ctx WHERE id = 1), 'add'),
                    '{table}', NEW.id, {new_label}, {new_json},
                    (SELECT user_id FROM session_context WHERE id = 1),
                    (SELECT username FROM session_context WHERE id = 1)
                );
            END
        """)

        connection.execute(f"""
            CREATE TRIGGER trg_hist_{table}_au AFTER UPDATE ON "{table}"
            WHEN {muted} AND {old_json} IS NOT {new_json}
            BEGIN
                INSERT INTO history(
                    action, entity, entity_id, label, old_data, new_data,
                    performed_by_user_id, performed_by_username
                )
                VALUES (
                    'edit', '{table}', NEW.id, {new_label}, {old_json}, {new_json},
                    (SELECT user_id FROM session_context WHERE id = 1),
                    (SELECT username FROM session_context WHERE id = 1)
                );
            END
        """)

        if is_parent:

            # log first, then mute the cascade / set-null noise
            connection.execute(f"""
                CREATE TRIGGER trg_hist_{table}_bd BEFORE DELETE ON "{table}"
                BEGIN
                    INSERT INTO history(
                        action, entity, entity_id, label, old_data,
                        performed_by_user_id, performed_by_username
                    )
                    SELECT
                        'delete', '{table}', OLD.id, {old_label}, {old_json},
                        (SELECT user_id FROM session_context WHERE id = 1),
                        (SELECT username FROM session_context WHERE id = 1)
                    WHERE {muted};

                    UPDATE history_ctx SET suppress = suppress + 1 WHERE id = 1;
                END
            """)

            connection.execute(f"""
                CREATE TRIGGER trg_hist_{table}_ad AFTER DELETE ON "{table}"
                BEGIN
                    UPDATE history_ctx
                    SET suppress = MAX(suppress - 1, 0) WHERE id = 1;
                END
            """)

        else:

            connection.execute(f"""
                CREATE TRIGGER trg_hist_{table}_ad AFTER DELETE ON "{table}"
                WHEN {muted}
                BEGIN
                    INSERT INTO history(
                        action, entity, entity_id, label, old_data,
                        performed_by_user_id, performed_by_username
                    )
                    VALUES (
                        'delete', '{table}', OLD.id, {old_label}, {old_json},
                        (SELECT user_id FROM session_context WHERE id = 1),
                        (SELECT username FROM session_context WHERE id = 1)
                    );
                END
            """)


# ----------------------------------------------------------------------
# Used by archive.py (muted cascades, one meaningful row per event)
# ----------------------------------------------------------------------

def set_session_user(user_id, username):
    """Called once, right after a successful login (see ui/login.py)."""

    connection = get_connection()

    try:
        connection.execute(
            "UPDATE session_context SET user_id = ?, username = ? WHERE id = 1",
            (user_id, username)
        )
        connection.commit()

    finally:
        connection.close()


def mute(cursor):
    cursor.execute("UPDATE history_ctx SET suppress = suppress + 1 WHERE id = 1")


def unmute(cursor):
    cursor.execute(
        "UPDATE history_ctx SET suppress = MAX(suppress - 1, 0) WHERE id = 1"
    )


def label_for(table, data):
    """Readable name for a record dict (python mirror of the SQL labels)."""

    data = data or {}

    if table == "projects":
        return f"{data.get('project_code', '')} - {data.get('project_name', '')}"

    if table == "expenses":
        return f"{data.get('title') or data.get('category') or ''} ({data.get('amount') or 0})"

    for key in ("contract_name", "title", "company_name", "full_name",
                "department_name", "phase_name"):
        if data.get(key):
            return str(data[key])

    return f"#{data.get('id', '?')}"


def log_event(cursor, action, entity, entity_id, label,
              old_data=None, new_data=None):
    """Manual row (archive delete / restore / purge)."""

    actor = cursor.execute(
        "SELECT user_id, username FROM session_context WHERE id = 1"
    ).fetchone()

    cursor.execute(
        """INSERT INTO history(
               action, entity, entity_id, label, old_data, new_data,
               performed_by_user_id, performed_by_username
           )
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            action, entity, entity_id, label,
            json.dumps(old_data, ensure_ascii=False) if old_data is not None else None,
            json.dumps(new_data, ensure_ascii=False) if new_data is not None else None,
            actor[0] if actor else None,
            actor[1] if actor else None,
        )
    )


# ----------------------------------------------------------------------
# Reading / clearing
# ----------------------------------------------------------------------

def get_history(search="", action="All", entity="All", limit=2000):

    sql = ("SELECT id, ts, action, entity, entity_id, label, old_data, new_data, "
           "performed_by_username FROM history WHERE 1 = 1")
    params = []

    if action and action != "All":
        sql += " AND action = ?"
        params.append(action.lower())

    if entity and entity != "All":
        key = next((k for k, v in ENTITY_TITLES.items() if v == entity), entity)
        sql += " AND entity = ?"
        params.append(key)

    if search:
        sql += " AND (label LIKE ? OR entity LIKE ? OR action LIKE ?)"
        like = f"%{search}%"
        params += [like, like, like]

    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    connection = get_connection()

    try:
        return connection.execute(sql, params).fetchall()
    finally:
        connection.close()


def get_data_version():
    """Changes whenever ANY tracked record changes (cheap: one query)."""

    connection = get_connection()

    try:
        return connection.execute(
            "SELECT COALESCE(MAX(id), 0) || ':' || COUNT(*) FROM history"
        ).fetchone()[0]
    except Exception:
        return "0"
    finally:
        connection.close()


def get_history_count():
    connection = get_connection()

    try:
        return connection.execute("SELECT COUNT(*) FROM history").fetchone()[0]
    finally:
        connection.close()


def clear_history():
    """Clear prior audit rows and leave a new audit record of the action."""
    with connect() as connection:
        require_session_permission(connection, "history.clear")
        deleted_count = connection.execute("SELECT COUNT(*) FROM history").fetchone()[0]
        connection.execute("DELETE FROM history")
        # Keep an auditable record that history was cleared and by whom.
        log_event(
            connection.cursor(), "clear", "history", None, "History cleared",
            old_data={"deleted_rows": deleted_count},
        )

    # VACUUM must run outside a transaction. Failure here does not undo the
    # already committed, auditable clear operation.
    connection = get_connection()
    try:
        connection.execute("VACUUM")
    finally:
        connection.close()


def describe_changes(old_json, new_json):
    """[(field, old, new)] for the details window."""

    try:
        old = json.loads(old_json) if old_json else {}
        new = json.loads(new_json) if new_json else {}
    except ValueError:
        return []

    keys = list(dict.fromkeys(list(old) + list(new)))

    rows = []

    for key in keys:
        before, after = old.get(key), new.get(key)

        if old and new and before == after:
            continue

        rows.append((key, "" if before is None else str(before),
                          "" if after is None else str(after)))

    return rows
