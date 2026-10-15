"""
Database bootstrap + migrations.

Replaces the old pile of one-off scripts (create_database.py, ..py,
insert_phases.py, migrate_expenses_table at import time ...).

init_database() is safe to call on every start:
  * fresh install  -> creates everything + default phases / departments
  * existing erp.db -> only adds what is missing
"""

import sqlite3

from .connection import connect, get_connection
from .history import install_triggers
from .schema import (
    TABLES,
    INDEXES,
    DEFAULT_PHASES,
    DEFAULT_DEPARTMENTS,
)

SCHEMA_VERSION = 5


# columns that older databases may be missing  (table, column, DDL)
_COLUMNS = [
    ("contracts", "client_id", "INTEGER"),
    ("expenses", "title", "TEXT"),
    ("expenses", "paid_by", "TEXT"),
    ("expenses", "status", "TEXT NOT NULL DEFAULT 'Pending'"),
    ("expenses", "project_phase_id", "INTEGER"),
    ("projects", "expected_price", "REAL DEFAULT 0"),
    ("projects", "current_phase_id", "INTEGER"),
    ("projects", "completion_date", "TEXT"),
    ("project_phases", "start_date", "TEXT"),
    ("project_phases", "end_date", "TEXT"),
    ("project_phases", "expected_price", "REAL DEFAULT 0"),
    ("history", "performed_by_user_id", "INTEGER"),
    ("history", "performed_by_username", "TEXT"),
]


def _columns(connection, table):
    return {
        row[1]
        for row in connection.execute(f'PRAGMA table_info("{table}")')
    }


def _ensure_columns(connection):
    for table, column, ddl in _COLUMNS:
        existing = _columns(connection, table)

        if existing and column not in existing:
            connection.execute(
                f'ALTER TABLE "{table}" ADD COLUMN "{column}" {ddl}'
            )


def _hash_legacy_passwords(connection):
    from security import hash_password, is_hashed

    rows = connection.execute(
        "SELECT id, password FROM users"
    ).fetchall()

    for user_id, password in rows:
        if password and not is_hashed(password):
            connection.execute(
                "UPDATE users SET password = ? WHERE id = ?",
                (hash_password(password), user_id)
            )


def _seed_defaults(connection):
    if connection.execute("SELECT COUNT(*) FROM phases").fetchone()[0] == 0:
        connection.executemany(
            "INSERT INTO phases(phase_name) VALUES(?)",
            [(name,) for name in DEFAULT_PHASES]
        )

    if connection.execute(
        "SELECT COUNT(*) FROM departments"
    ).fetchone()[0] == 0:
        connection.executemany(
            "INSERT INTO departments(department_name) VALUES(?)",
            [(name,) for name in DEFAULT_DEPARTMENTS]
        )


def _rebuild_without_checks():
    """
    projects / project_phases used CHECK(... IN (...)) lists, which makes it
    impossible to add a new status / type / priority.  SQLite cannot drop a
    CHECK, so the tables are rebuilt (official 12-step procedure) - all ids,
    rows and relations are kept.
    """

    connection = get_connection()

    try:

        def current_sql(name):
            row = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                (name,)
            ).fetchone()
            return (row[0] if row else "").upper()

        names = set()

        # projects / project_phases: used CHECK(... IN (...)) status lists,
        # which block adding a new status/type/priority from Settings.
        for name in ("projects", "project_phases"):
            if "CHECK" in current_sql(name):
                names.add(name)

        # documents: project_id used to be NOT NULL, but the "No Project"
        # option in the Add Document screen sets it to NULL, which used
        # to crash with "NOT NULL constraint failed: documents.project_id".
        documents_sql = current_sql("documents")

        if "PROJECT_ID INTEGER NOT NULL" in documents_sql:
            names.add("documents")

        # users: username used to be case-sensitively UNIQUE, so "sahand"
        # and "Sahand" could exist as two different accounts.
        users_sql = current_sql("users")

        if "USERNAME TEXT UNIQUE COLLATE NOCASE" not in users_sql and \
           "USERNAME TEXT UNIQUE COLLATE \"NOCASE\"" not in users_sql:

            if "USERNAME" in users_sql:

                duplicates = connection.execute("""
                    SELECT LOWER(username), COUNT(*) FROM users
                    WHERE username IS NOT NULL
                    GROUP BY LOWER(username)
                    HAVING COUNT(*) > 1
                """).fetchall()

                if duplicates:
                    # Don't silently merge/delete accounts - surface this
                    # and let an admin rename one of them first. The rest
                    # of the migration (projects/documents/...) still runs.
                    names_list = ", ".join(d[0] for d in duplicates)
                    raise RuntimeError(
                        "Cannot enforce unique usernames: these usernames "
                        f"exist more than once (differing only by case): "
                        f"{names_list}. Rename one of each pair in "
                        "Settings -> Lists -> Managers, then restart."
                    )

                names.add("users")

        if not names:
            return

        connection.execute("PRAGMA foreign_keys = OFF")

        for name in names:

            create = next(
                sql for sql in TABLES
                if f"CREATE TABLE IF NOT EXISTS {name}(" in sql
            ).replace(
                f"CREATE TABLE IF NOT EXISTS {name}(",
                f"CREATE TABLE {name}_new(", 1
            )

            old_columns = [r[1] for r in connection.execute(f'PRAGMA table_info("{name}")')]

            seq = connection.execute(
                "SELECT seq FROM sqlite_sequence WHERE name = ?", (name,)
            ).fetchone()

            connection.execute("BEGIN")
            connection.execute(f'DROP TABLE IF EXISTS "{name}_new"')
            connection.execute(create)

            new_columns = [r[1] for r in connection.execute(f'PRAGMA table_info("{name}_new")')]
            shared = ", ".join(f'"{c}"' for c in old_columns if c in new_columns)

            try:

                connection.execute(
                    f'INSERT INTO "{name}_new" ({shared}) SELECT {shared} FROM "{name}"'
                )

                connection.execute(f'DROP TABLE "{name}"')
                connection.execute(f'ALTER TABLE "{name}_new" RENAME TO "{name}"')

                if seq:
                    connection.execute(
                        "UPDATE sqlite_sequence SET seq = ? WHERE name = ?", (seq[0], name)
                    )

                bad = connection.execute("PRAGMA foreign_key_check").fetchall()

                if bad:
                    raise RuntimeError(f"Migration of {name} broke relations: {bad[:3]}")

            except Exception:
                connection.execute("ROLLBACK")
                raise

            connection.execute("COMMIT")

        connection.execute("PRAGMA foreign_keys = ON")

    finally:
        connection.close()


def init_database():
    # A schema upgrade can rebuild tables. Preserve an integrity-checked
    # backup before touching an existing database with an older schema.
    from pathlib import Path
    from paths import DB_PATH
    existing_db = Path(DB_PATH)
    if existing_db.is_file() and existing_db.stat().st_size > 0:
        probe = sqlite3.connect(f"file:{existing_db.as_posix()}?mode=ro", uri=True)
        try:
            has_tables = probe.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' LIMIT 1"
            ).fetchone() is not None
            old_version = probe.execute("PRAGMA user_version").fetchone()[0]
        finally:
            probe.close()
        if has_tables and old_version < SCHEMA_VERSION:
            from .backup import create_backup
            try:
                create_backup(existing_db)
            except Exception as error:
                raise RuntimeError(
                    "Database migration was stopped because a verified pre-migration "
                    f"backup could not be created: {error}"
                ) from error

    with connect() as connection:

        for statement in TABLES:
            connection.execute(statement)

        _ensure_columns(connection)

    _rebuild_without_checks()

    with connect() as connection:

        for statement in INDEXES:
            connection.execute(statement)

        connection.execute(
            "INSERT OR IGNORE INTO history_ctx(id, action, suppress) VALUES (1, NULL, 0)"
        )
        connection.execute("UPDATE history_ctx SET suppress = 0 WHERE id = 1")

        _seed_defaults(connection)

        from .lookups import seed_lookups
        seed_lookups(connection)

        from .permissions import seed_roles
        seed_roles(connection)

        # triggers LAST: the seeding above must not appear in the history
        install_triggers(connection)

        version = connection.execute(
            "PRAGMA user_version"
        ).fetchone()[0]

        if version < 2:
            _hash_legacy_passwords(connection)

        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
