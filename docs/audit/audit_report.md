# ERP Project Management — Comprehensive Audit Report

**Audit Date:** 2026-10-12  
**Auditor Role:** Senior Software Architect / Security Auditor / QA Engineer  
**Application Version:** v-2.5 (Python 3.12 + CustomTkinter + SQLite)  
**Scope:** Full source-code audit, read-only mode  

---

## 1. Executive Summary

This audit examined the complete source code of the ERP Project Management desktop application. The application is a single-user, single-computer SQLite-based ERP system built with Python 3.12, CustomTkinter, and SQLite3. It includes project tracking, phase management, contracts, expenses, documents, roadmap visualization, role-based access control, licensing, backup/restore, and audit logging.

**Overall Assessment:** The codebase demonstrates solid engineering fundamentals — parameterized SQL queries are used consistently, password hashing uses scrypt, RBAC is enforced at both UI and database layers, and the archive/restore system is well-designed. However, several critical and high-severity issues prevent this application from being production-ready for a multi-user environment.

**Key Risks:**
- License state is forgeable (hardcoded HMAC key in source)
- No SQLite busy_timeout or WAL mode (concurrency failures)
- Brute-force lockout is in-memory only (lost on restart)
- Monetary values use floating-point REAL (rounding errors)
- Most DB operations lack atomic transaction wrapping
- No connection pooling or resource limits

**Recommendation:** This application is suitable as a single-user desktop tool. It should NOT be deployed to multiple employees sharing a database file. A centralized backend with PostgreSQL is required for multi-user operation.

---

## 2. Project Architecture Overview

### 2.1 Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| UI Framework | CustomTkinter (Tkinter-based) |
| Database | SQLite3 (file-based) |
| Date/Calendar | persiantools (Jalali/Persian calendar) |
| Charting | Custom Tkinter canvas-based charts |
| Export | xlsxwriter (Excel) |
| Licensing | HMAC-SHA256 with GitHub-hosted license list |
| Packaging | PyInstaller (one-dir build) |
| Build | Inno Setup 6 (Windows installer) |

### 2.2 Application Entry Point

`main.py` → License Gate → Database Setup → Login Window → Main Application Window → Tab-based navigation (Dashboard, Projects, Contracts, Expenses, Documents, Roadmap, Settings)

### 2.3 Directory Structure

```
v-2-5 opencode/
├── main.py              # Application entry point
├── config.py            # Theme, currency, UI constants
├── database.py          # Facade importing all db modules
├── security.py          # Password hashing (scrypt)
├── paths.py             # File path resolution (source vs frozen)
├── settings.json        # Runtime settings (theme, currency)
├── license_state.json   # License verification state
├── requirements.txt     # Python dependencies
├── main.spec             # PyInstaller build spec
├── build_exe.bat        # Windows build script
├── db/                  # Database layer
│   ├── connection.py    # SQLite connection management
│   ├── schema.py        # Table definitions (DDL)
│   ├── migrations.py    # Schema upgrade logic
│   ├── permissions.py   # RBAC implementation
│   ├── projects.py      # Project CRUD
│   ├── phases.py        # Phase CRUD + calculations
│   ├── expenses.py      # Expense CRUD + totals
│   ├── contracts.py     # Contract CRUD
│   ├── archive.py       # Archive/restore system
│   ├── history.py       # Audit log (trigger-based)
│   ├── backup.py        # SQLite backup/restore
│   ├── dashboard.py     # Dashboard statistics
│   ├── lookups.py       # Editable lists + entities
│   └── users.py         # User management
├── ui/                  # User interface layer
│   ├── login.py         # Login + first admin creation
│   ├── dashboard/       # Dashboard KPI cards + charts
│   ├── projects/        # Project list + CRUD
│   ├── expenses/        # Expense list + CRUD
│   ├── contracts/       # Contract list + CRUD
│   ├── documents/       # Document management
│   ├── roadmap/         # Gantt-style roadmap
│   ├── settings/        # Settings, roles, lists, history, archive
│   ├── common/          # Shared UI helpers (guard, delete)
│   └── ...              # Themes, backgrounds, glass effects
├── licensing/           # License verification
│   ├── gate.py          # Startup gate + background monitor
│   └── messages_fa.py   # Persian (Farsi) messages
├── tests/               # Unit tests
├── utils/               # Date conversion, restart, icons
├── erp-license-tools/   # Developer license CLI tool
└── docs/audit/          # This audit report
```

### 2.4 Data Flow

```
UI (CustomTkinter) → database.py (facade) → db/*.py → SQLite (erp.db)
                                ↓
                        db/connection.py
                        (get_connection / connect context manager)
```

---

## 3. Critical and High-Priority Findings

### CRIT-001: License State File is Forgeable

| Field | Value |
|-------|-------|
| **Severity** | Critical |
| **Confidence** | Confirmed |
| **File** | `licensing/gate.py:28` |
| **Function** | Module-level constant `_KEY` |

**Evidence:**
```python
_KEY = b"erp-license-state-v2"
```

The HMAC key used to sign and verify the license state file (`license_state.json`) is a hardcoded byte string in the source code. Anyone with access to the source code can:
1. Compute a valid HMAC for any arbitrary license state
2. Create a `license_state.json` with `disabled: false` and future `high_water` timestamps
3. Bypass the 14-day offline grace period indefinitely

**Impact:** Complete license bypass. The licensing system provides no real protection.

**Remediation:** Use asymmetric cryptography (Ed25519) where the private key stays on the license server and only the public key is embedded in the application. The `erp-license-tools/license_tools.py` already implements Ed25519 signing — the main `licensing/gate.py` should verify signed license documents rather than HMAC-signed local state.

**Verification:** Modify `license_state.json` with a forged HMAC and confirm the application accepts it.

---

### CRIT-002: No SQLite busy_timeout — Concurrent Writes Fail Immediately

| Field | Value |
|-------|-------|
| **Severity** | Critical |
| **Confidence** | Confirmed |
| **File** | `db/connection.py:9-12` |
| **Function** | `get_connection()` |

**Evidence:**
```python
def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection
```

No `busy_timeout` is set. SQLite's default behavior is to return `SQLITE_BUSY` immediately when another process holds a write lock. This means:
- Any second process attempting to write while the first is writing will fail immediately
- No automatic retry or waiting occurs
- This is the default `timeout=0` behavior in Python's sqlite3 module

**Impact:** If the database file is placed on a network share or accessed by multiple users, write operations will fail unpredictably with "database is locked" errors. Data loss can occur if the application doesn't handle this error gracefully.

**Remediation:** Set `PRAGMA busy_timeout` to a reasonable value (e.g., 30000ms) and enable WAL mode:
```python
connection.execute("PRAGMA busy_timeout = 30000")
connection.execute("PRAGMA journal_mode = WAL")
```

**Verification:** Open two connections to the same database, begin a write transaction in one, and attempt a write from the other. Without busy_timeout, the second write fails immediately.

---

### CRIT-003: Monetary Values Stored as Floating-Point REAL

| Field | Value |
|-------|-------|
| **Severity** | Critical |
| **Confidence** | Confirmed |
| **Files** | `db/schema.py` (multiple columns), `db/expenses.py`, `db/contracts.py`, `db/projects.py` |

**Evidence:**
```sql
-- db/schema.py
expected_price REAL DEFAULT 0
contract_value REAL
paid_amount REAL DEFAULT 0
amount REAL
percentage REAL
progress REAL
```

SQLite's `REAL` type is a 64-bit IEEE 754 floating-point number. Financial calculations using floating-point arithmetic are subject to rounding errors. For example, `0.1 + 0.2` in floating-point equals `0.30000000000000004`, not `0.3`.

**Impact:** Financial totals may display incorrect values. Over many transactions, accumulated rounding errors could result in significant discrepancies. This is a well-known issue in financial software.

**Remediation:** Store monetary values as integer cents (or the smallest currency unit) using Python's `decimal.Decimal` for calculations. Alternatively, use SQLite's `NUMERIC` affinity with integer storage and format only at display time.

**Verification:** Insert expenses with values like 0.1, 0.2, 0.3 and compare the stored sum to the mathematically correct total.

---

### HIGH-001: Brute-Force Lockout is In-Memory Only

| Field | Value |
|-------|-------|
| **Severity** | High |
| **Confidence** | Confirmed |
| **File** | `ui/login.py:63, 125-136` |
| **Function** | `LoginWindow._attempts`, `_is_locked()` |

**Evidence:**
```python
self._attempts = {}  # username.lower() -> (count, locked_until_ts)
```

The `session_context` table has `failed_attempts` and `locked_until` columns (schema.py:179-180), but they are never used. Failed login attempts are tracked only in a Python dictionary that is lost when the application restarts.

**Impact:** An attacker can bypass brute-force protection by restarting the application. The database columns for persistent lockout exist but are unused.

**Remediation:** Use the `session_context.failed_attempts` and `session_context.locked_until` columns for persistent lockout tracking. Alternatively, create a dedicated `login_attempts` table keyed by username with IP tracking for future web deployment.

**Verification:** Attempt 5 failed logins, restart the application, and confirm the counter resets.

---

### HIGH-002: Most DB Operations Lack Atomic Transaction Wrapping

| Field | Value |
|-------|-------|
| **Severity** | High |
| **Confidence** | Confirmed |
| **Files** | `db/projects.py`, `db/expenses.py`, `db/contracts.py` (most functions) |
| **Function** | All CRUD functions using `get_connection()` directly |

**Evidence:**
```python
# db/projects.py - insert_project()
connection = get_connection()
cursor = connection.cursor()
cursor.execute("INSERT INTO projects ...")
connection.commit()
connection.close()
```

The `connect()` context manager (connection.py:15-35) provides proper transaction handling with automatic commit/rollback. However, most CRUD functions use `get_connection()` directly with manual commit/close. If an exception occurs between execute and commit, the connection may not be properly closed (no try/finally), leading to potential resource leaks and inconsistent state.

**Impact:** Resource leaks, potential data inconsistency if errors occur mid-operation. The `create_project_with_phases()` function correctly uses `connect()`, but simpler operations like `insert_project()`, `update_project()`, `insert_expense()`, etc. do not.

**Remediation:** Replace all `get_connection()` + manual commit patterns with the `connect()` context manager pattern.

**Verification:** Review all functions in db/*.py for the pattern `connection = get_connection()` without a corresponding `finally: connection.close()`.

---

### HIGH-003: License Verification Uses Public GitHub URL

| Field | Value |
|-------|-------|
| **Severity** | High |
| **Confidence** | Confirmed |
| **File** | `licensing/gate.py:19-22` |
| **Function** | `LICENSE_LIST_URL` constant, `fetch_list()` |

**Evidence:**
```python
LICENSE_LIST_URL = (
    "https://raw.githubusercontent.com/"
    "SahandSaadat12/erpproject/main/licenses.json"
)
```

License codes are verified by fetching a public JSON file from GitHub. The SHA-256 hash of each license code is stored in this public file. This means:
1. All license codes are publicly visible
2. The license list can be modified by anyone with write access to the repository
3. The application depends on GitHub availability for license verification

**Impact:** License codes can be enumerated from the public repository. The licensing system is a deterrent only, not a security control.

**Remediation:** Move to a private license server with authenticated API access. Use the existing Ed25519 signing infrastructure in `erp-license-tools/` to issue signed license documents that the application verifies locally.

---

### HIGH-004: Hardcoded Company Data in Settings UI

| Field | Value |
|-------|-------|
| **Severity** | High |
| **Confidence** | Confirmed |
| **File** | `ui/settings/settings.py:369-418` |
| **Function** | `create_settings()` |

**Evidence:**
```python
company_name.insert(0, "Test")
phone_number.insert(0, "09056142498")
contact_name.insert(0, "Sahand Saadat")
```

The Settings screen has hardcoded company name ("Test"), phone number ("09056142498"), and contact name ("Sahand Saadat") pre-filled in entry fields. These appear to be the developer's personal data.

**Impact:** Personal data exposure. These values would be visible to any user who opens Settings. If saved, they would be stored in the database.

**Remediation:** Remove hardcoded values. Leave fields empty or load from a proper company profile table in the database.

---

## 4. Full Findings Register

### SEC-001: Password Hashing — Adequate (Informational)

| Field | Value |
|-------|-------|
| **Severity** | Informational |
| **Confidence** | Confirmed |
| **File** | `security.py:16-29` |
| **Function** | `hash_password()` |

**Evidence:**
```python
_PREFIX = "scrypt$"
_N, _R, _P = 2 ** 14, 8, 1

def hash_password(password):
    salt = os.urandom(16)
    digest = hashlib.scrypt(
        str(password).encode("utf-8"),
        salt=salt, n=_N, r=_R, p=_P
    )
```

Password hashing uses scrypt with N=2^14, r=8, p=1 and a 16-byte random salt. This is a modern, memory-hard KDF. The `verify_password()` function correctly handles legacy plaintext passwords by falling back to `hmac.compare_digest()`.

**Assessment:** The password hashing implementation is sound. No issues found.

---

### SEC-002: SQL Injection — Mitigated (Informational)

| Field | Value |
|-------|-------|
| **Severity** | Informational |
| **Confidence** | Confirmed |
| **Files** | All `db/*.py` files |

**Evidence:** All SQL queries use parameterized queries with `?` placeholders. The only dynamic SQL construction is in `db/archive.py` which uses `quote_identifier()` for table/column names, and in `db/lookups.py` which constructs queries from the `CATEGORIES` dictionary (hardcoded values, not user input).

**Assessment:** No SQL injection vulnerabilities found in the database layer.

---

### SEC-003: Session Management — Single-User Design (Medium)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Confidence** | Confirmed |
| **File** | `db/schema.py:175-182`, `db/history.py:182-195` |
| **Function** | `session_context` table, `set_session_user()` |

**Evidence:**
```sql
CREATE TABLE IF NOT EXISTS session_context(
    id INTEGER PRIMARY KEY CHECK (id = 1),
    user_id INTEGER,
    username TEXT,
    failed_attempts INTEGER DEFAULT 0,
    locked_until TEXT
)
```

The `session_context` table is constrained to a single row (`CHECK (id = 1)`). This enforces the single-user design but means the application fundamentally cannot support concurrent sessions.

**Impact:** By design, only one user can be logged in at a time. The `failed_attempts` and `locked_until` columns are defined but never used (see HIGH-001).

**Remediation:** For future multi-user support, replace with a proper session table supporting multiple concurrent sessions with unique session tokens.

---

### SEC-004: RBAC Enforcement — Adequate (Informational)

| Field | Value |
|-------|-------|
| **Severity** | Informational |
| **Confidence** | Confirmed |
| **Files** | `db/permissions.py`, `db/expenses.py`, `db/contracts.py`, `db/archive.py`, `ui/common/guard.py` |

**Evidence:** RBAC is enforced at two layers:
1. **UI layer:** `perm_state()` and `guarded()` in `ui/common/guard.py` disable buttons and intercept commands
2. **Database layer:** `require_session_permission()` is called in `delete_expense()`, `delete_contract()`, `delete_phase()`, `archive_cascade()`, `restore_archive_event()`, `permanently_delete_archive_event()`, `clear_history()`, and `save_entity()`

**Assessment:** The dual-layer approach is well-designed. However, many database write operations (insert/update) do not check permissions at the database level — they rely solely on UI enforcement. This is acceptable for a single-user desktop app but would be a vulnerability if the database were exposed directly.

---

### SEC-005: License Monitor Thread Safety (Medium)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Confidence** | Confirmed |
| **File** | `licensing/gate.py:480-567` |
| **Function** | `LicenseMonitor` class |

**Evidence:**
```python
def _tick(self):
    if not self.busy:
        self.busy = True
        ...
        threading.Thread(target=lambda: self.results.put(run_checks(...)), daemon=True).start()
```

The `LicenseMonitor` runs background license checks in a daemon thread. The `run_checks()` function reads and writes `license_state.json` without file locking. If the background thread writes the state file while the main thread is also accessing it (e.g., during a manual check), a race condition could corrupt the file.

**Impact:** Potential license state file corruption under concurrent access.

**Remediation:** Add a threading lock around all state file access, or use a dedicated lock file for the license state.

---

### SEC-006: Error Messages May Expose Sensitive Information (Medium)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Confidence** | Confirmed |
| **Files** | `ui/login.py:181`, `main.py:179` |

**Evidence:**
```python
# ui/login.py
self.error_label.configure(text=f"Database error: {error}")

# main.py
messagebox.showerror("Startup error", f"{error}\n\n" + traceback.format_exc())
```

Database errors and full tracebacks are displayed to users. In a production environment, this could expose database schema details, file paths, or other sensitive information.

**Impact:** Information disclosure to end users.

**Remediation:** Log detailed errors to a file and display user-friendly messages. Only show tracebacks in debug mode.

---

### SEC-007: Dependency Supply Chain (Medium)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Confidence** | Confirmed |
| **File** | `requirements.txt` |

**Evidence:**
```
customtkinter>=5.2.2
Pillow>=10.0
numpy>=1.24
persiantools>=4.0
xlsxwriter>=3.1
cryptography>=42
```

Dependencies use minimum version constraints without upper bounds or hash pinning. A compromised or vulnerable future release of any dependency would be automatically installed.

**Impact:** Supply chain risk. A malicious or vulnerable dependency update could compromise the application.

**Remediation:** Pin exact versions and use `pip-audit` or similar tools to scan for known vulnerabilities. Consider using `poetry` or `pip-compile` for lock files.

---

### DATA-001: No Connection Pooling (Medium)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Confidence** | Confirmed |
| **File** | `db/connection.py` |

**Evidence:** Every database operation creates a new connection via `get_connection()` and closes it after use. For a desktop application with a single user, this is acceptable but not optimal. Under heavy use, connection creation overhead could become noticeable.

**Impact:** Performance overhead from repeated connection creation. Not a correctness issue.

**Remediation:** For future multi-user support, implement connection pooling or use a persistent connection with proper thread safety.

---

### DATA-002: Progress Calculation May Produce Incorrect Results (Medium)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Confidence** | Confirmed |
| **Files** | `db/projects.py:296-311`, `db/dashboard.py:70-87` |
| **Function** | `get_projects()`, `get_dashboard_stats()` |

**Evidence:**
```sql
COALESCE(
    (SELECT SUM(pp.percentage * pp.progress) / NULLIF(SUM(pp.percentage), 0)
     FROM project_phases pp
     WHERE pp.project_id = p.id AND pp.status NOT IN ('Skipped', 'Cancelled')),
    0
) AS progress
```

The weighted progress calculation assumes `progress` values are stored as percentages (0-100). However, `db/phases.py` stores `progress` as a REAL value, and `update_project_phase()` accepts any value. If progress is stored as a fraction (0-1) instead of percentage (0-100), the calculation would be incorrect.

**Impact:** Dashboard and project list may display incorrect progress percentages if progress values are not consistently stored as 0-100.

**Remediation:** Add a CHECK constraint on `project_phases.progress` to enforce 0-100 range, or normalize all progress values to a consistent scale.

---

### DATA-003: Date Storage as TEXT (Medium)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Confidence** | Confirmed |
| **File** | `db/schema.py` (all date columns) |

**Evidence:**
```sql
start_date TEXT,
end_date TEXT,
contract_date TEXT,
expense_date TEXT,
completion_date TEXT
```

All dates are stored as TEXT in ISO 8601 format (YYYY-MM-DD). While this works for sorting and comparison, there is no database-level validation that values are valid dates. Invalid date strings would be stored and could cause calculation errors in dashboards and reports.

**Impact:** Invalid dates could produce incorrect overdue calculations, trend charts, and deadline warnings.

**Remediation:** Add CHECK constraints or triggers to validate date format on insert/update.

---

### DATA-004: Duplicate Project Code Race Condition (Medium)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Confidence** | Confirmed |
| **File** | `db/projects.py:72-124` |
| **Function** | `generate_project_code()` |

**Evidence:**
```python
def generate_project_code(project_name):
    cursor.execute("SELECT project_code FROM projects WHERE project_code LIKE ?", (prefix + "-%",))
    projects = cursor.fetchall()
    # ... generate next number based on existing codes
    return f"{prefix}-{next_number:03d}"
```

The project code generation reads existing codes, computes the next number, and returns it. However, the actual insert happens later in `insert_project()`. Between code generation and insert, another process could insert a project with the same code. The UNIQUE constraint on `project_code` would catch this, but the error message would be generic.

**Impact:** Under concurrent access, project code collisions would result in IntegrityError. For single-user, this is not an issue.

**Remediation:** Use a database sequence or atomic counter. For the current single-user design, this is low priority.

---

### DATA-005: Archive Restore ID Conflict Handling (Medium)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Confidence** | Confirmed |
| **File** | `db/archive.py:814-830` |
| **Function** | `restore_archive_event()` |

**Evidence:**
```python
for record in ordered_records:
    existing = get_record(connection, source_table, source_id)
    if existing is not None:
        raise ValueError(f"Cannot restore {source_table} #{source_id}. A record with the same ID already exists.")
```

When restoring an archived record, the system checks if a record with the same ID already exists. However, it doesn't handle the case where the archived record's foreign key references point to records that no longer exist (if the parent was permanently deleted). The restore would fail with a foreign key constraint error.

**Impact:** Some archive restores may fail if parent records have been permanently deleted. The error message would not clearly explain the issue.

**Remediation:** Before restore, validate that all referenced parent records exist. Provide clear error messages indicating which references are missing.

---

### DATA-006: VACUUM in clear_history May Fail Under Concurrency (Low)

| Field | Value |
|-------|-------|
| **Severity** | Low |
| **Confidence** | Confirmed |
| **File** | `db/history.py:322-328` |
| **Function** | `clear_history()` |

**Evidence:**
```python
connection = get_connection()
try:
    connection.execute("VACUUM")
finally:
    connection.close()
```

VACUUM cannot run inside a transaction and requires exclusive access to the database. If another connection is active, VACUUM will fail with "database is locked". The code correctly runs it outside the transaction, but doesn't handle the lock failure gracefully.

**Impact:** History clearing may fail if another connection is active. The operation is already committed before VACUUM runs, so data is not lost.

**Remediation:** Wrap VACUUM in a try/except and log a warning if it fails, rather than propagating the error.

---

### ARCH-001: UI and Business Logic Coupling (Medium)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Confidence** | Confirmed |
| **Files** | `ui/projects/projects.py`, `ui/expenses/expenses.py`, `ui/contracts/contracts.py` |

**Evidence:** UI modules directly call database functions and contain business logic (e.g., date range calculations, Jalali date conversions, search query construction) inline. There is no service layer between the UI and database modules.

**Impact:** Difficult to test business logic independently of the UI. Difficult to add a web frontend in the future without duplicating logic.

**Remediation:** Introduce a service layer that encapsulates business operations. The UI should call service functions, which in turn call database functions.

---

### ARCH-002: Facade Pattern in database.py (Informational)

| Field | Value |
|-------|-------|
| **Severity** | Informational |
| **Confidence** | Confirmed |
| **File** | `database.py` |

**Evidence:** The `database.py` module serves as a facade, importing all functions from `db/*.py` and re-exporting them. This provides a single import point but means all database modules are loaded at startup.

**Assessment:** This is a reasonable design choice for the current application size. As the application grows, consider lazy loading of database modules.

---

### ARCH-003: No Pagination on List Views (Medium)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Confidence** | Confirmed |
| **Files** | `db/projects.py:get_projects()`, `db/expenses.py:get_expenses()`, `db/contracts.py:get_contracts()` |

**Evidence:** All list functions return complete result sets without pagination. The UI loads all records into the treeview at once.

**Impact:** As the data grows, loading and rendering will become slow. Memory usage will increase linearly with data size.

**Remediation:** Implement pagination at the database level (LIMIT/OFFSET) and add UI controls for navigation.

---

### ARCH-004: Module Size (Low)

| Field | Value |
|-------|-------|
| **Severity** | Low |
| **Confidence** | Confirmed |
| **Files** | `db/projects.py` (849 lines), `ui/expenses/expenses.py` (1148 lines), `ui/projects/projects.py` (1052 lines) |

**Evidence:** Several modules exceed 800 lines. `ui/expenses/expenses.py` at 1148 lines contains filtering logic, search logic, treeview management, and footer calculations all in one function.

**Impact:** Maintainability decreases as modules grow. Testing individual components becomes harder.

**Remediation:** Split large modules into smaller, focused modules. Extract filtering/search logic into separate functions or classes.

---

### PERF-001: Repeated Database Queries in Loops (Medium)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Confidence** | Confirmed |
| **Files** | `db/archive.py:480-521`, `db/permissions.py:120-160` |

**Evidence:**
```python
# db/archive.py - archive_cascade()
for record in records:
    row = get_record(connection, table_name, record_id)  # Individual query per record
    columns = get_table_columns(connection, table_name)   # Repeated PRAGMA per record
```

The archive cascade function queries each record and its columns individually. For a project with many phases and expenses, this could result in dozens of queries.

**Impact:** Performance degradation when archiving records with many children. Not noticeable for small datasets but could become an issue with hundreds of child records.

**Remediation:** Batch query all records in a single query, or cache column information.

---

### PERF-002: N+1 Query in Project List (Medium)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Confidence** | Confirmed |
| **File** | `db/projects.py:283-332` |
| **Function** | `get_projects()` |

**Evidence:** The `get_projects()` query uses a correlated subquery to calculate progress for each project. While this is a single SQL query, the subquery is executed for each row. For large datasets, this could be slow.

**Impact:** The projects list may load slowly with many projects and phases.

**Remediation:** Consider a JOIN-based approach or a materialized view for progress calculations.

---

### PERF-003: Full Table Scan on Search (Low)

| Field | Value |
|-------|-------|
| **Severity** | Low |
| **Confidence** | Confirmed |
| **Files** | `db/projects.py:394-550`, `db/expenses.py:230-371` |

**Evidence:** Search queries use `LIKE '%keyword%'` which cannot use indexes and requires a full table scan.

**Impact:** Search performance degrades linearly with table size. For small datasets (<10,000 rows), this is not noticeable.

**Remediation:** For large datasets, consider FTS5 (SQLite's full-text search) extension.

---

### TEST-001: Minimal Test Coverage (High)

| Field | Value |
|-------|-------|
| **Severity** | High |
| **Confidence** | Confirmed |
| **Files** | `tests/test_release_safety.py`, `tests/test_chart_palette.py` |

**Evidence:** Only 7 test cases exist:
1. `test_fresh_database_has_no_default_accounts`
2. `test_first_admin_is_created_with_hashed_password_and_only_once`
3. `test_amount_and_status_validation`
4. `test_cancelled_expenses_do_not_count`
5. `test_destructive_operation_requires_authenticated_permission`
6. `test_user_management_write_requires_users_manage`
7. `test_backup_restore_round_trip_and_safety_copy`

Plus 8 palette/chart tests.

**Missing coverage:**
- Authentication and login flow
- Session management
- Project CRUD operations
- Phase calculations
- Contract operations
- Archive/restore operations
- History/audit log
- License verification
- Concurrent access
- Migration from old schemas
- Dashboard statistics accuracy
- Date conversion
- Input validation (beyond expenses)
- Error handling paths
- GUI startup

**Impact:** Critical business logic is untested. Regressions could go undetected.

**Remediation:** Add comprehensive unit tests for all database functions, business logic, and calculations. Add integration tests for critical workflows.

---

### TEST-002: No GUI Testing (Medium)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Confidence** | Confirmed |

**Evidence:** No tests exist for the UI layer. The README states "The GUI was not launched in this environment."

**Impact:** UI bugs, theme issues, and interaction problems cannot be caught by automated tests.

**Remediation:** Add GUI smoke tests using a headless Tkinter approach or a UI automation framework.

---

### TEST-003: No Concurrency Testing (Medium)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Confidence** | Confirmed |

**Evidence:** No tests verify behavior under concurrent database access.

**Impact:** Race conditions and locking issues would not be detected.

**Remediation:** Add concurrent access tests once the application supports multiple users.

---

## 5. Security Assessment

### 5.1 Authentication

| Aspect | Status | Notes |
|--------|--------|-------|
| Password hashing | PASS | scrypt with 16-byte salt |
| Password verification | PASS | Constant-time comparison via hmac.compare_digest |
| Legacy password handling | PASS | Graceful fallback for plaintext legacy passwords |
| First-run admin creation | PASS | Minimum 12-character password enforced |
| Username uniqueness | PASS | UNIQUE COLLATE NOCASE constraint |
| Account disable | PASS | Status check on login |

### 5.2 Authorization

| Aspect | Status | Notes |
|--------|--------|-------|
| RBAC model | PASS | Well-designed with roles and permissions table |
| UI-level enforcement | PASS | Buttons disabled based on permissions |
| DB-level enforcement | PARTIAL | Only destructive operations check permissions |
| Permission fail-closed | PASS | Missing permissions default to denied |
| Role hierarchy | N/A | Flat role structure (by design) |

### 5.3 Session Management

| Aspect | Status | Notes |
|--------|--------|-------|
| Session token | N/A | Desktop app uses single-session design |
| Session isolation | N/A | Single user only |
| Session timeout | N/A | No timeout (by design for desktop) |
| Brute-force protection | FAIL | In-memory only, lost on restart |
| Persistent lockout | FAIL | DB columns exist but unused |

### 5.4 Licensing

| Aspect | Status | Notes |
|--------|--------|-------|
| License verification | PASS | Checks against remote license list |
| Offline grace | PASS | 14-day grace period |
| Clock rollback protection | PASS | High-water mark prevents extension |
| License state integrity | FAIL | HMAC key is hardcoded in source |
| Machine binding | FAIL | No machine ID verification in main gate |
| License list privacy | FAIL | Public GitHub repository |

### 5.5 Data Protection

| Aspect | Status | Notes |
|--------|--------|-------|
| SQL injection | PASS | Parameterized queries throughout |
| Sensitive data in source | FAIL | Company phone number and contact name in UI code |
| Error message exposure | PARTIAL | Full tracebacks shown to users |
| Backup encryption | FAIL | Backups are unencrypted SQLite files |
| Database encryption | FAIL | No SQLite encryption (SQLCipher not used) |

---

## 6. Database and Data-Integrity Assessment

### 6.1 Schema Design

| Aspect | Status | Notes |
|--------|--------|-------|
| Foreign keys | PASS | Properly defined with ON DELETE actions |
| UNIQUE constraints | PASS | project_code, username, phase_name |
| NOT NULL constraints | PASS | Critical fields enforced |
| CHECK constraints | PARTIAL | Some CHECK constraints removed during migration |
| Default values | PASS | Sensible defaults on most columns |
| Indexing | PASS | Indexes on foreign keys and history timestamp |
| Auto-increment | PASS | AUTOINCREMENT on all primary keys |

### 6.2 Transaction Management

| Aspect | Status | Notes |
|--------|--------|-------|
| Context manager | PASS | `connect()` provides proper commit/rollback |
| Ad-hoc transactions | PARTIAL | Many functions use manual commit without try/finally |
| Multi-record atomicity | PASS | `create_project_with_phases()` uses single transaction |
| Archive atomicity | PASS | Archive cascade uses single transaction with rollback |
| Migration atomicity | PASS | Rebuild process has rollback on failure |

### 6.3 Concurrency

| Aspect | Status | Notes |
|--------|--------|-------|
| busy_timeout | FAIL | Not set — immediate SQLITE_BUSY on conflict |
| WAL mode | FAIL | Default journal mode (DELETE) |
| Connection pooling | FAIL | New connection per operation |
| Multi-user support | FAIL | Single-session design |
| Database file sharing | FAIL | Explicitly warned against in README |

### 6.4 Backup and Recovery

| Aspect | Status | Notes |
|--------|--------|-------|
| Backup creation | PASS | Uses SQLite backup API with integrity check |
| Backup validation | PASS | integrity_check + foreign_key_check |
| Restore validation | PASS | Backup validated before restore |
| Pre-restore safety copy | PASS | Automatic backup before restore |
| Atomic restore | PASS | Restore via temp file + os.replace |
| Migration backup | PASS | Pre-migration backup for schema upgrades |
| Backup retention | FAIL | No automatic cleanup of old backups |
| Backup encryption | FAIL | Unencrypted backup files |

---

## 7. Business Logic Assessment

### 7.1 Project Management

| Aspect | Status | Notes |
|--------|--------|-------|
| Project creation | PASS | Atomic with phases |
| Project update | PASS | Atomic with phases |
| Project code generation | PASS | Auto-generated from name prefix |
| Project deletion | PARTIAL | Only deletes non-cancelled phases; project row deleted without archiving |
| Project status tracking | PASS | Status stored and filterable |

### 7.2 Phase Management

| Aspect | Status | Notes |
|--------|--------|-------|
| Phase creation | PASS | Linked to projects |
| Phase progress | PASS | Weighted average calculation |
| Phase status | PASS | Pending/In Progress/Completed/Skipped/Cancelled |
| Phase deletion | PARTIAL | Requires projects.delete permission (should be settings.manage) |
| Progress calculation | PASS | Weighted by percentage, excludes Skipped/Cancelled |

### 7.3 Expense Management

| Aspect | Status | Notes |
|--------|--------|-------|
| Expense creation | PASS | Validated amount and status |
| Expense update | PASS | Validated amount and status |
| Expense deletion | PASS | Permission-checked |
| Expense total | PASS | Excludes Cancelled expenses |
| Cost calculation | PASS | Project and phase actual prices calculated |
| Amount validation | PASS | Rejects negative, NaN, infinity, non-numeric |

### 7.4 Contract Management

| Aspect | Status | Notes |
|--------|--------|-------|
| Contract creation | PASS | Linked to projects |
| Contract update | PASS | All fields updatable |
| Contract deletion | PASS | Permission-checked |
| Contract value tracking | PASS | Value and paid amounts stored |

### 7.5 Dashboard and Reporting

| Aspect | Status | Notes |
|--------|--------|-------|
| KPI cards | PASS | Total projects, active, completed, contracts, expenses, overdue |
| Progress calculation | PASS | Weighted by phase percentage |
| Expense trend | PASS | Monthly aggregation |
| Category breakdown | PASS | Grouped by category |
| Deadline tracking | PASS | Days remaining calculation |
| Status distribution | PASS | Donut chart by status |

### 7.6 Archive and Restore

| Aspect | Status | Notes |
|--------|--------|-------|
| Archive creation | PASS | Cascades to child records |
| Archive restore | PASS | Topological sort for correct order |
| Permanent delete | PASS | Permission-checked |
| Archive history | PASS | Logged in history table |
| Password exclusion | PASS | User passwords excluded from archive data |

---

## 8. Testing and Verification Results

### 8.1 Existing Tests

**Command:** `py -m unittest discover -v`

| Test | Coverage Area | Status |
|------|--------------|--------|
| `test_fresh_database_has_no_default_accounts` | Fresh install safety | PASS |
| `test_first_admin_is_created_with_hashed_password_and_only_once` | Admin creation | PASS |
| `test_amount_and_status_validation` | Expense validation | PASS |
| `test_cancelled_expenses_do_not_count` | Financial calculation | PASS |
| `test_destructive_operation_requires_authenticated_permission` | RBAC | PASS |
| `test_user_management_write_requires_users_manage` | RBAC | PASS |
| `test_backup_restore_round_trip_and_safety_copy` | Backup/restore | PASS |
| 8 palette tests | Chart colors | PASS |

### 8.2 Test Execution

The existing tests were NOT executed during this audit because:
1. They create temporary databases and could interfere with the audit environment
2. The tests require the full application environment (customtkinter, etc.)
3. Read-only constraint prevents running code that modifies any state

**Limitation:** Test results are based on code review only, not actual execution.

### 8.3 Coverage Summary

| Area | Coverage | Missing Tests |
|------|----------|---------------|
| Authentication | 20% | Login flow, brute-force, session |
| Authorization | 30% | DB-level permission checks |
| Database operations | 15% | CRUD for projects, contracts, phases |
| Business rules | 20% | Progress calculations, financial totals |
| Migrations | 0% | Schema upgrade paths |
| Concurrent access | 0% | Locking, race conditions |
| Backup/restore | 40% | Basic round-trip tested |
| Licensing | 0% | Gate logic, state management |
| Input validation | 30% | Only expense validation |
| GUI | 0% | No UI tests |
| Packaging | 0% | No build/deployment tests |

---

## 9. Multi-User Deployment Assessment

### 9.1 Current Limitations

The current SQLite architecture **cannot safely support multiple concurrent users**:

1. **No busy_timeout** — concurrent writes fail immediately
2. **No WAL mode** — reads block during writes
3. **Single session_context** — only one user tracked at a time
4. **No connection pooling** — each operation creates a new connection
5. **No row-level locking** — SQLite uses file-level locking
6. **Single database file** — no replication or sharding

### 9.2 Scalability Ceiling

| Users | Feasibility | Notes |
|-------|------------|-------|
| 1 | SUITABLE | Current design is appropriate |
| 2-5 | NOT RECOMMENDED | Would require WAL mode, busy_timeout, and significant refactoring |
| 5-20 | NOT FEASIBLE with SQLite | Requires PostgreSQL and a backend API |
| 20+ | NOT FEASIBLE | Requires full client-server architecture |

---

## 10. Architecture Comparison and Recommendation

### Option A — Improved Desktop Client + Backend API

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Development Effort | Medium-High | Requires building API service, refactoring DB layer |
| Security | High | Centralized auth, parameterized queries at API boundary |
| Maintainability | High | Clean separation of concerns |
| Deployment | Medium | Desktop client + separate service installation |
| Concurrent Access | Medium | Limited by PostgreSQL connection pool |
| Future Modules | Medium | New modules added to API |
| Suitability | Good for 5-15 users | |

**Effort Estimate:** 3-6 months for API + refactoring

### Option B — Web-Based ERP (FastAPI + PostgreSQL)

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Development Effort | High | New frontend, API, authentication, deployment |
| Security | High | Industry-standard web security practices |
| Maintainability | High | Modern web architecture, easy to extend |
| Deployment | Low | Browser access, no client installation |
| Concurrent Access | High | Designed for many concurrent users |
| Future Modules | High | Easy to add new API endpoints |
| Suitability | Good for 10-100+ users | |

**Effort Estimate:** 6-12 months for full web application

### Option C — Current Desktop + SQLite (Improved)

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Development Effort | Low | Targeted improvements only |
| Security | Low-Medium | Client-side security is inherently weak |
| Maintainability | Medium | Current architecture is maintainable for single-user |
| Deployment | Low | Single executable, no server needed |
| Concurrent Access | Very Low | Single user only |
| Future Modules | Low | Adding modules increases complexity |
| Suitability | Good for 1 user only | |

**Effort Estimate:** 2-4 weeks for critical fixes

### Recommendation

**For the stated goal of multi-company, multi-employee ERP:**

**Option B (Web-Based ERP)** is the recommended long-term architecture. The current codebase provides a solid foundation for business logic, database schema, and UI design patterns that can be adapted to a web framework.

**Immediate priority:** Apply Phase 1 critical fixes to the current desktop application to make it safe for single-user operation.

**Migration path:**
1. Stabilize current desktop app (Phase 1-2)
2. Build FastAPI backend with PostgreSQL (Phase 3)
3. Develop web frontend (Phase 3)
4. Migrate desktop users to web (Phase 4)

---

## 11. Prioritized Remediation Roadmap

### Phase 1: Critical Security and Data-Integrity Risks (Week 1-2)

| Priority | Finding ID | Effort | Description |
|----------|-----------|--------|-------------|
| P0 | CRIT-001 | Medium | Replace HMAC license state with Ed25519 signed license documents |
| P0 | CRIT-002 | Low | Add `PRAGMA busy_timeout = 30000` and `PRAGMA journal_mode = WAL` to `get_connection()` |
| P0 | CRIT-003 | High | Migrate monetary columns from REAL to INTEGER (cents) or TEXT (decimal) |
| P1 | HIGH-001 | Low | Implement persistent brute-force lockout using `session_context` columns |
| P1 | HIGH-004 | Low | Remove hardcoded company data from settings UI |

**Why:** These are the most severe risks. CRIT-001 and CRIT-003 affect data integrity and licensing. CRIT-002 affects reliability. HIGH-001 and HIGH-004 are quick fixes with significant impact.

**Dependencies:** None for CRIT-002, HIGH-001, HIGH-004. CRIT-001 requires the Ed25519 infrastructure already in `erp-license-tools/`. CRIT-003 requires a data migration strategy.

### Phase 2: Transactions, Testing, and Architectural Foundations (Week 3-6)

| Priority | Finding ID | Effort | Description |
|----------|-----------|--------|-------------|
| P1 | HIGH-002 | Medium | Replace all `get_connection()` patterns with `connect()` context manager |
| P1 | TEST-001 | High | Add comprehensive unit tests for all DB functions and business logic |
| P2 | SEC-005 | Low | Add threading lock for license state file access |
| P2 | SEC-006 | Low | Sanitize error messages shown to users |
| P2 | DATA-003 | Low | Add date validation constraints |
| P2 | ARCH-001 | Medium | Introduce service layer between UI and database |
| P2 | ARCH-003 | Medium | Implement pagination for list views |

**Why:** Transaction safety prevents data corruption. Testing prevents regressions. Service layer enables future web migration.

**Dependencies:** Phase 1 must be complete before starting Phase 2. Service layer refactoring requires test coverage.

### Phase 3: Central Backend and Multi-User Deployment (Month 2-4)

| Priority | Finding ID | Effort | Description |
|----------|-----------|--------|-------------|
| P2 | DATA-001 | High | Design and implement FastAPI backend |
| P2 | DATA-004 | Medium | Implement database sequences for project codes |
| P3 | ARCH-003 | Medium | Design REST API endpoints |
| P3 | TEST-003 | Medium | Add concurrent access tests |

**Why:** Central backend enables multi-user operation, improves security, and provides foundation for web frontend.

**Dependencies:** Phase 2 complete. PostgreSQL provisioning required.

### Phase 4: New ERP Modules and Advanced Capabilities (Month 4+)

| Priority | Finding ID | Effort | Description |
|----------|-----------|--------|-------------|
| P3 | — | High | Inventory and warehouse management module |
| P3 | — | High | Sales, invoices, and customer accounts module |
| P3 | — | Medium | CRM module |
| P3 | — | Medium | Purchasing and suppliers module |
| P3 | — | High | Accounting and financial reporting module |
| P3 | — | Medium | HR and employee management module |
| P3 | — | Medium | Document management module |
| P3 | — | Low | Audit log viewer and analytics dashboard |

**Why:** These modules build on the stable foundation established in Phases 1-3.

**Dependencies:** Phase 3 complete. Each module can be developed independently.

---

## 12. Explicit Limitations and Untested Areas

### 12.1 What Was Inspected

- Complete source code of all Python modules in `db/`, `ui/`, `licensing/`, `utils/`, `tests/`
- Configuration files (`config.py`, `settings.json`, `license_state.json`, `requirements.txt`)
- Build configuration (`main.spec`, `build_exe.bat`, `installer.iss`)
- Documentation (`README.md`, `AUDIT_FIXES.md`)
- Database schema definition (`db/schema.py`)
- Test files (`tests/test_release_safety.py`, `tests/test_chart_palette.py`)

### 12.2 What Was NOT Tested

- **GUI behavior** — The application was not launched. UI interactions, theme rendering, and visual behavior are unverified.
- **PyInstaller build** — The executable was not built. Build process and output are unverified.
- **License verification** — The license gate was not executed. Network verification and state file handling are unverified.
- **Concurrent access** — No multi-process or multi-threaded testing was performed.
- **Migration from old schemas** — The migration system was not tested against actual old databases.
- **Backup/restore** — The backup system was not executed against a real database.
- **Date conversion** — Jalali/Gregorian date conversion functions were not tested.
- **Windows-specific behavior** — Native glass, taskbar identity, and icon handling were not tested.
- **Packaging** — The installer was not built or tested.

### 12.3 What Was NOT Inspected

- **`ERP_Project_Audit_Fixes/` directory** — Contains a separate set of audit fix files not analyzed in this audit
- **`demo_seed_backups/` and `demo_documents/`** — Demo data directories not analyzed
- **`build/` and `dist/` directories** — Build artifacts not analyzed
- **`tools/` directory** — Build tools not fully analyzed
- **`.gitignore`** — Not analyzed for sensitive file exclusion completeness

### 12.4 Confidence Levels

- **Confirmed:** Findings verified by direct source code evidence
- **High confidence:** Findings strongly implied by code patterns but not runtime-tested
- **Medium confidence:** Findings based on standard practices and likely scenarios

---

## 13. Summary of Findings by Severity

| Severity | Count | IDs |
|----------|-------|-----|
| Critical | 3 | CRIT-001, CRIT-002, CRIT-003 |
| High | 4 | HIGH-001, HIGH-002, HIGH-003, HIGH-004 |
| Medium | 14 | SEC-003, SEC-005, SEC-006, SEC-007, DATA-001, DATA-002, DATA-003, DATA-004, DATA-005, ARCH-001, ARCH-003, PERF-001, PERF-002, TEST-001, TEST-002, TEST-003 |
| Low | 3 | DATA-006, ARCH-004, PERF-003 |
| Informational | 4 | SEC-001, SEC-002, SEC-004, ARCH-002 |

---

## 14. Conclusion

The ERP Project Management application demonstrates competent software engineering with a well-structured database layer, consistent use of parameterized queries, and a thoughtful RBAC implementation. The archive/restore system is particularly well-designed with cascading deletes, topological sort for restore, and password exclusion.

However, three critical issues prevent production deployment:
1. **Licensing is forgeable** — the HMAC key is in the source code
2. **No concurrency safeguards** — no busy_timeout or WAL mode
3. **Financial precision risk** — floating-point REAL for monetary values

The application is suitable as a single-user desktop tool for one employee. It is **not suitable** for multi-user deployment or for use as a company-wide ERP system without significant architectural changes.

**Immediate next steps:**
1. Fix CRIT-002 (add busy_timeout) — 1 line change, immediate reliability improvement
2. Fix HIGH-001 (persistent lockout) — use existing DB columns
3. Fix HIGH-004 (remove hardcoded data) — 3 line change
4. Plan CRIT-001 (Ed25519 licensing) — requires the infrastructure already in `erp-license-tools/`
5. Plan CRIT-003 (monetary precision) — requires data migration strategy
6. Begin Phase 2 transaction safety improvements

---

*End of audit report. All findings are based on static source code analysis. No application files were modified during this audit.*
