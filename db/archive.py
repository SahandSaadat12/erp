import json
import sqlite3
import uuid
from datetime import datetime

import os
from pathlib import Path

from .connection import get_connection
from .permissions import require_session_permission
from .history import mute, unmute, log_event, label_for


# =========================================================
# Helpers
# =========================================================

def quote_identifier(identifier):
    return '"' + str(identifier).replace('"', '""') + '"'


def get_table_names(connection):
    cursor = connection.cursor()

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)

    return [row[0] for row in cursor.fetchall()]


def get_foreign_keys(connection, table_name):
    cursor = connection.cursor()

    cursor.execute(
        f"""
        PRAGMA foreign_key_list(
            {quote_identifier(table_name)}
        )
        """
    )

    return cursor.fetchall()


def get_table_columns(connection, table_name):
    cursor = connection.cursor()

    cursor.execute(
        f"""
        PRAGMA table_info(
            {quote_identifier(table_name)}
        )
        """
    )

    return [row[1] for row in cursor.fetchall()]


def get_record(connection, table_name, record_id):
    cursor = connection.cursor()

    cursor.execute(
        f"""
        SELECT *
        FROM {quote_identifier(table_name)}
        WHERE id = ?
        """,
        (record_id,)
    )

    return cursor.fetchone()


# =========================================================
# Archive Table
# =========================================================

def create_archive_table():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS archive (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_table TEXT NOT NULL,
                source_id INTEGER NOT NULL,
                data TEXT NOT NULL,
                deleted_at TEXT NOT NULL,
                archive_group_id TEXT
            )
        """)

        # ---------------------------------------------
        # Migration for old archive table
        # ---------------------------------------------

        cursor.execute("""
            PRAGMA table_info(archive)
        """)

        columns = [
            row[1]
            for row in cursor.fetchall()
        ]

        if "archive_group_id" not in columns:

            cursor.execute("""
                ALTER TABLE archive
                ADD COLUMN archive_group_id TEXT
            """)

        # ---------------------------------------------
        # Give old archive records their own groups
        # ---------------------------------------------

        cursor.execute("""
            SELECT id
            FROM archive
            WHERE archive_group_id IS NULL
        """)

        old_records = cursor.fetchall()

        for row in old_records:

            archive_id = row[0]

            cursor.execute("""
                UPDATE archive
                SET archive_group_id = ?
                WHERE id = ?
            """, (
                f"legacy-{archive_id}",
                archive_id
            ))

        # ---------------------------------------------
        # Index
        # ---------------------------------------------

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_archive_group_id
            ON archive(archive_group_id)
        """)

        connection.commit()

    finally:
        connection.close()


# =========================================================
# Find Child Records
# =========================================================

def find_child_records(
    connection,
    source_table,
    source_id
):
    """
    Finds records that directly reference:

        source_table.id = source_id

    Example:

        expenses.project_id -> projects.id
    """

    tables = get_table_names(connection)

    children = []

    for table_name in tables:

        if table_name == "archive":
            continue

        if table_name == source_table:
            continue

        foreign_keys = get_foreign_keys(
            connection,
            table_name
        )

        for foreign_key in foreign_keys:

            target_table = foreign_key[2]
            source_column = foreign_key[3]
            target_column = foreign_key[4]

            if target_table != source_table:
                continue

            cursor = connection.cursor()

            cursor.execute(
                f"""
                SELECT id
                FROM {quote_identifier(table_name)}
                WHERE {quote_identifier(source_column)} = ?
                """,
                (source_id,)
            )

            rows = cursor.fetchall()

            for row in rows:

                child_id = row[0]

                children.append({
                    "table": table_name,
                    "id": child_id
                })

    return children


# =========================================================
# Collect Cascade
# =========================================================

def collect_cascade(
    connection,
    source_table,
    source_id
):
    """
    Recursively collects all child records.

    Parent is NOT included automatically.
    """

    collected = []
    visited = set()

    def visit(table_name, record_id):

        key = (
            table_name,
            record_id
        )

        if key in visited:
            return

        visited.add(key)

        children = find_child_records(
            connection,
            table_name,
            record_id
        )

        for child in children:

            child_table = child["table"]
            child_id = child["id"]

            visit(
                child_table,
                child_id
            )

            child_key = (
                child_table,
                child_id
            )

            if child_key not in [
                (
                    item["table"],
                    item["id"]
                )
                for item in collected
            ]:

                collected.append({
                    "table": child_table,
                    "id": child_id
                })

    visit(
        source_table,
        source_id
    )

    # Parent itself must be first in archive.
    result = [
        {
            "table": source_table,
            "id": source_id
        }
    ]

    result.extend(collected)

    return result


# =========================================================
# Archive One Record
# =========================================================

def archive_record(
    source_table,
    source_id,
    archive_group_id=None,
    connection=None
):
    close_connection = False

    if connection is None:
        connection = get_connection()
        close_connection = True

    try:

        record = get_record(
            connection,
            source_table,
            source_id
        )

        if record is None:
            raise ValueError(
                f"Record not found: "
                f"{source_table} #{source_id}"
            )

        columns = get_table_columns(
            connection,
            source_table
        )

        record_data = dict(
            zip(columns, record)
        )

        if archive_group_id is None:
            archive_group_id = str(
                uuid.uuid4()
            )

        deleted_at = datetime.now().isoformat(
            timespec="seconds"
        )

        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO archive (
                source_table,
                source_id,
                data,
                deleted_at,
                archive_group_id
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            source_table,
            source_id,
            json.dumps(
                record_data,
                ensure_ascii=False
            ),
            deleted_at,
            archive_group_id
        ))

        if close_connection:
            connection.commit()

        return archive_group_id

    finally:

        if close_connection:
            connection.close()


# =========================================================
# Archive Cascade
# =========================================================

def archive_cascade(
    source_table,
    source_id
):
    """
    Archives the selected record and every
    child record recursively, then deletes them
    from the live database.

    Returns archive_group_id.
    """

    connection = get_connection()

    permission_by_table = {
        "projects": "projects.delete",
        "contracts": "contracts.delete",
        "expenses": "expenses.delete",
        "documents": "documents.delete",
        "users": "users.manage",
        "clients": "clients.manage",
        "departments": "settings.manage",
        "phases": "settings.manage",
    }
    try:
        if source_table not in permission_by_table:
            raise ValueError(f"Archiving table '{source_table}' is not supported.")
        require_session_permission(connection, permission_by_table[source_table])
    except Exception:
        connection.close()
        raise

    try:

        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        cursor = connection.cursor()

        # ---------------------------------------------
        # Check source record
        # ---------------------------------------------

        source_record = get_record(
            connection,
            source_table,
            source_id
        )

        if source_record is None:
            raise ValueError(
                f"Record not found: "
                f"{source_table} #{source_id}"
            )

        # ---------------------------------------------
        # Collect everything
        # ---------------------------------------------

        records = collect_cascade(
            connection,
            source_table,
            source_id
        )

        # ---------------------------------------------
        # New event
        # ---------------------------------------------

        archive_group_id = str(
            uuid.uuid4()
        )

        deleted_at = datetime.now().isoformat(
            timespec="seconds"
        )

        # ---------------------------------------------
        # Archive all records FIRST
        # ---------------------------------------------

        for record in records:

            table_name = record["table"]
            record_id = record["id"]

            row = get_record(
                connection,
                table_name,
                record_id
            )

            if row is None:
                continue

            columns = get_table_columns(
                connection,
                table_name
            )

            record_data = dict(
                zip(columns, row)
            )

            cursor.execute("""
                INSERT INTO archive (
                    source_table,
                    source_id,
                    data,
                    deleted_at,
                    archive_group_id
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                table_name,
                record_id,
                json.dumps(
                    record_data,
                    ensure_ascii=False
                ),
                deleted_at,
                archive_group_id
            ))

        # ---------------------------------------------
        # Delete children first  (history: ONE row, not one per child)
        # ---------------------------------------------

        source_columns = get_table_columns(connection, source_table)
        source_data = dict(zip(source_columns, source_record))
        source_data.pop("password", None)

        mute(cursor)

        for record in reversed(records):

            table_name = record["table"]
            record_id = record["id"]

            cursor.execute(
                f"""
                DELETE FROM {quote_identifier(table_name)}
                WHERE id = ?
                """,
                (record_id,)
            )

        unmute(cursor)

        label = label_for(source_table, source_data)

        if len(records) > 1:
            label += f"  (+{len(records) - 1} related)"

        log_event(
            cursor, "delete", source_table, source_id, label,
            old_data=source_data
        )

        connection.commit()

        return archive_group_id

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


# =========================================================
# Get Archive Records
# =========================================================

def get_archived_records():
    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                id,
                source_table,
                source_id,
                data,
                deleted_at,
                archive_group_id
            FROM archive
            ORDER BY id DESC
        """)

        return cursor.fetchall()

    finally:

        connection.close()


# =========================================================
# Get Archive Event
# =========================================================

def get_archive_event(
    archive_group_id
):
    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                id,
                source_table,
                source_id,
                data,
                deleted_at,
                archive_group_id
            FROM archive
            WHERE archive_group_id = ?
            ORDER BY id ASC
        """, (
            archive_group_id,
        ))

        return cursor.fetchall()

    finally:

        connection.close()


# =========================================================
# Topological Sort For Restore
# =========================================================

def sort_records_for_restore(
    connection,
    records
):
    """
    Parents must be inserted before children.

    Example:

        projects
            ↓
        expenses

    projects is restored first.
    """

    record_map = {}

    for record in records:

        source_table = record[1]
        source_id = record[2]

        record_map[
            (source_table, source_id)
        ] = record

    # ---------------------------------------------
    # Graph
    # ---------------------------------------------

    dependencies = {
        key: set()
        for key in record_map
    }

    for key, record in record_map.items():

        table_name = key[0]

        try:
            data = json.loads(
                record[3]
            )
        except (json.JSONDecodeError, TypeError):
            data = {}

        foreign_keys = get_foreign_keys(
            connection,
            table_name
        )

        for foreign_key in foreign_keys:

            foreign_column = foreign_key[3]
            target_table = foreign_key[2]
            target_column = foreign_key[4]

            if target_column != "id":
                continue

            foreign_value = data.get(
                foreign_column
            )

            if foreign_value is None:
                continue

            parent_key = (
                target_table,
                foreign_value
            )

            if parent_key in record_map:
                dependencies[key].add(
                    parent_key
                )

    # ---------------------------------------------
    # Kahn's algorithm
    # ---------------------------------------------

    sorted_keys = []

    remaining = {
        key: set(value)
        for key, value in dependencies.items()
    }

    while remaining:

        ready = [
            key
            for key, deps in remaining.items()
            if not deps
        ]

        if not ready:
            raise ValueError(
                "Cannot restore archive event because "
                "a circular foreign-key dependency exists."
            )

        ready.sort(
            key=lambda item: record_map[item][0]
        )

        for key in ready:

            sorted_keys.append(key)
            del remaining[key]

        for deps in remaining.values():

            for key in ready:
                deps.discard(key)

    return [
        record_map[key]
        for key in sorted_keys
    ]


# =========================================================
# Restore Archive Event
# =========================================================

def restore_archive_event(
    archive_group_id
):
    connection = get_connection()

    try:
        require_session_permission(connection, "archive.restore")
        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                id,
                source_table,
                source_id,
                data,
                deleted_at,
                archive_group_id
            FROM archive
            WHERE archive_group_id = ?
            ORDER BY id ASC
        """, (
            archive_group_id,
        ))

        records = cursor.fetchall()

        if not records:
            return False

        # ---------------------------------------------
        # Sort parent -> child
        # ---------------------------------------------

        ordered_records = sort_records_for_restore(
            connection,
            records
        )

        # ---------------------------------------------
        # Check if any record already exists
        # ---------------------------------------------

        for record in ordered_records:

            source_table = record[1]
            source_id = record[2]

            existing = get_record(
                connection,
                source_table,
                source_id
            )

            if existing is not None:
                raise ValueError(
                    f"Cannot restore "
                    f"{source_table} #{source_id}. "
                    f"A record with the same ID already exists."
                )

        # ---------------------------------------------
        # Restore
        # ---------------------------------------------

        mute(cursor)

        for record in ordered_records:

            source_table = record[1]
            source_id = record[2]
            data_json = record[3]

            data = json.loads(
                data_json
            )

            columns = get_table_columns(
                connection,
                source_table
            )

            # Keep only real table columns
            # and preserve original ID.
            insert_columns = [
                column
                for column in columns
                if column in data
            ]

            values = [
                data[column]
                for column in insert_columns
            ]

            column_sql = ", ".join(
                quote_identifier(column)
                for column in insert_columns
            )

            placeholders = ", ".join(
                "?"
                for _ in insert_columns
            )

            cursor.execute(
                f"""
                INSERT INTO {quote_identifier(source_table)}
                ({column_sql})
                VALUES ({placeholders})
                """,
                values
            )

        unmute(cursor)

        top = ordered_records[0]
        top_data = json.loads(top[3])
        top_data.pop("password", None)

        label = label_for(top[1], top_data)

        if len(ordered_records) > 1:
            label += f"  (+{len(ordered_records) - 1} related)"

        log_event(
            cursor, "restore", top[1], top[2], label,
            new_data=top_data
        )

        # ---------------------------------------------
        # Delete archive event ONLY after
        # successful restoration
        # ---------------------------------------------

        cursor.execute("""
            DELETE FROM archive
            WHERE archive_group_id = ?
        """, (
            archive_group_id,
        ))

        connection.commit()

        return True

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()



# =========================================================
# Permanent Delete Archive Event
# =========================================================

def permanently_delete_archive_event(
    archive_group_id
):
    connection = get_connection()

    try:
        require_session_permission(connection, "archive.permanent_delete")
    except Exception:
        connection.close()
        raise

    try:

        cursor = connection.cursor()

        # ---------------------------------------------
        # Get archive records FIRST
        # ---------------------------------------------

        cursor.execute("""
            SELECT
                id,
                source_table,
                source_id,
                data,
                deleted_at,
                archive_group_id
            FROM archive
            WHERE archive_group_id = ?
            ORDER BY id ASC
        """, (
            archive_group_id,
        ))

        records = cursor.fetchall()

        if not records:
            return False

        top_data = json.loads(records[0][3])
        top_data.pop("password", None)

        label = label_for(records[0][1], top_data)

        if len(records) > 1:
            label += f"  (+{len(records) - 1} related)"

        log_event(
            cursor, "purge", records[0][1], records[0][2], label,
            old_data=top_data
        )

        # ---------------------------------------------
        # Delete from SQLite archive
        # ---------------------------------------------

        cursor.execute("""
            DELETE FROM archive
            WHERE archive_group_id = ?
        """, (
            archive_group_id,
        ))

        connection.commit()

        return True

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()

def archive_single_record(source_table, source_id):
    connection = get_connection()

    permission_by_table = {
        "projects": "projects.delete", "contracts": "contracts.delete",
        "expenses": "expenses.delete", "documents": "documents.delete",
        "users": "users.manage", "clients": "clients.manage",
        "departments": "settings.manage", "phases": "settings.manage",
    }
    try:
        if source_table not in permission_by_table:
            raise ValueError(f"Archiving table '{source_table}' is not supported.")
        require_session_permission(connection, permission_by_table[source_table])
        connection.execute("PRAGMA foreign_keys = ON")

        record = get_record(connection, source_table, source_id)

        if record is None:
            raise ValueError(
                f"Record not found: {source_table} #{source_id}"
            )

        archive_group_id = str(uuid.uuid4())

        archive_record(
            source_table,
            source_id,
            archive_group_id=archive_group_id,
            connection=connection
        )

        cursor = connection.cursor()

        columns = get_table_columns(connection, source_table)
        data = dict(zip(columns, record))
        data.pop("password", None)

        mute(cursor)

        cursor.execute(
            f"""
            DELETE FROM {quote_identifier(source_table)}
            WHERE id = ?
            """,
            (source_id,)
        )

        unmute(cursor)

        log_event(
            cursor, "delete", source_table, source_id,
            label_for(source_table, data), old_data=data
        )

        connection.commit()

        return archive_group_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()