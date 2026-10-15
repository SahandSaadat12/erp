# ERP Remediation Plan — Verified Backlog

**Date:** 2026-10-12  
**Based on:** Comprehensive Audit Report (docs/audit/audit_report.md)  
**Scope:** Single-user desktop application stabilization  
**Constraint:** Read-only — no source modifications  

---

## Finding Verification Summary

| ID | Original Severity | Verified Severity | Status | Notes |
|----|-------------------|-------------------|--------|-------|
| CRIT-001 | Critical | Critical | Confirmed defect | HMAC key in source |
| CRIT-002 | Critical | Medium (single-user) / Critical (multi-user) | Confirmed defect | No busy_timeout; background thread creates real concurrency |
| CRIT-003 | Critical | Critical | Confirmed defect | REAL columns for money |
| HIGH-001 | High | High | Confirmed defect | Lockout in-memory only |
| HIGH-002 | High | Medium | Confirmed defect (downgraded) | Resource leak risk, not data corruption |
| HIGH-003 | High | High | Confirmed defect | Public license list |
| HIGH-004 | High | Low | Confirmed defect (downgraded) | Demo data, not a security vulnerability |

### Downgrades Explained

- **HIGH-002 → Medium:** The non-atomic pattern leaks connections on unhandled exceptions but does not corrupt data. For a short-lived desktop app, the impact is limited resource waste. The `connect()` context manager exists and is used in critical paths (project+phases, archive). The remaining functions are simple single-statement inserts/updates where the commit-immediately-after pattern is functionally equivalent to a transaction.
- **HIGH-004 → Low:** Hardcoded company name, phone, and contact name in settings.py is demo data visible in source code. It is not a security vulnerability — the data is already exposed in the source. It is a code hygiene issue.

### Additional Finding: Background Thread Concurrency

The `LicenseMonitor` (gate.py:480-567) runs a daemon thread that calls `run_checks()`, which reads and writes `license_state.json`. The main thread also reads this file at startup. This creates a real race condition even in single-user mode, making CRIT-002 more relevant than initially assessed.

---

## Part A: Single-User Desktop Fixes

These fixes apply to the current single-user, single-computer SQLite application.

### A-001: Add SQLite busy_timeout and WAL Mode

| Field | Value |
|-------|-------|
| **Addresses** | CRIT-002 |
| **File** | `db/connection.py` |
| **Function** | `get_connection()` (line 9) |
| **Current code** | `connection = sqlite3.connect(DB_PATH); connection.execute("PRAGMA foreign_keys = ON") |
| **Proposed change** | Add `PRAGMA busy_timeout = 30000` and `PRAGMA journal_mode = WAL` after connect |
| **Type** | Confirmed defect — fix |
| **Why it matters** | The LicenseMonitor background thread writes to the same database file. Without busy_timeout, any main-thread write during a background write fails immediately with SQLITE_BUSY. WAL allows concurrent reads during writes. |
| **Does NOT make shared network safe** | WAL + busy_timeout only help for local file access. SQLite on a network share still has file-locking limitations. This fix does NOT enable multi-user deployment. |
| **Dependencies** | None |
| **Migration risk** | None — WAL mode is persistent but can be reverted |
| **Regression risk** | Low — WAL creates additional -wal and -shm files; backup logic already uses SQLite backup API which handles WAL correctly |
| **Acceptance criteria** | 1. `PRAGMA journal_mode` returns `wal` after change. 2. Main thread writes succeed while background thread holds a read. 3. Existing backup/restore tests pass. 4. Application starts and operates normally. |
| **Safe test** | Run existing test suite; add a test that begins a write on one connection and verifies the other connection waits rather than failing |

---

### A-002: Implement Persistent Brute-Force Lockout

| Field | Value |
|-------|-------|
| **Addresses** | HIGH-001 |
| **File** | `ui/login.py` |
| **Function** | `LoginWindow.__init__` (line 63), `_is_locked` (line 125), `_try_login` (line 138) |
| **Current code** | `self._attempts = {}` — in-memory dict, lost on restart |
| **Proposed change** | Write failed attempts to `session_context.failed_attempts` and `session_context.locked_until`; read from DB on login attempt |
| **Type** | Confirmed defect — fix |
| **Why it matters** | An attacker can reset the lockout counter by restarting the application. The database columns already exist but are unused. |
| **Dependencies** | A-001 (busy_timeout) to avoid DB contention during concurrent access |
| **Migration risk** | None — columns already exist in schema |
| **Regression risk** | Low — only affects login flow; must ensure first-run (no users) path still works |
| **Acceptance criteria** | 1. 5 failed logins lock the username for 60 seconds. 2. Restarting the app preserves the lockout. 3. Successful login resets the counter. 4. First-run admin creation is unaffected. |
| **Safe test** | Unit test: simulate 5 failed attempts, verify lockout persists across LoginWindow re-instantiation |

---

### A-003: Remove Hardcoded Company Data from Settings

| Field | Value |
|-------|-------|
| **Addresses** | HIGH-004 |
| **File** | `ui/settings/settings.py` |
| **Function** | `create_settings()` (lines 369-418) |
| **Current code** | `company_name.insert(0, "Test")`, `phone_number.insert(0, "09056142498")`, `contact_name.insert(0, "Sahand Saadat")` |
| **Proposed change** | Remove the three `.insert(0, ...)` calls; leave fields empty or load from a company profile table |
| **Type** | Confirmed defect (code hygiene) — fix |
| **Why it matters** | The developer's personal phone number and name are pre-filled in the settings form. This data is visible to any user and would be stored if saved. |
| **Dependencies** | None |
| **Migration risk** | None |
| **Regression risk** | None — purely cosmetic change |
| **Acceptance criteria** | 1. Settings form opens with empty company fields. 2. No hardcoded personal data remains in source. |
| **Safe test** | Code review — verify no `.insert(0,` calls remain in settings.py |

---

### A-004: Sanitize User-Facing Error Messages

| Field | Value |
|-------|-------|
| **Addresses** | SEC-006 (from full findings) |
| **File** | `ui/login.py` line 181, `main.py` lines 179, 253 |
| **Function** | `LoginWindow._try_login`, `main.startup error handlers` |
| **Current code** | `self.error_label.configure(text=f"Database error: {error}")` and `traceback.format_exc()` shown to user |
| **Proposed change** | Log full error to a file; display generic message ("An error occurred. Check the log for details.") |
| **Type** | Confirmed defect — fix |
| **Why it matters** | Database errors and tracebacks expose schema details, file paths, and internal structure to end users. |
| **Dependencies** | None |
| **Migration risk** | None |
| **Regression risk** | Low — must ensure error logging still captures full details for debugging |
| **Acceptance criteria** | 1. Failed login shows generic message, not raw DB error. 2. Startup errors log traceback to file. 3. Existing tests pass. |
| **Safe test** | Trigger a DB error during login; verify user sees generic message and log file contains details |

---

### A-005: Fix License Monitor Thread Safety

| Field | Value |
|-------|-------|
| **Addresses** | SEC-005 (from full findings) |
| **File** | `licensing/gate.py` |
| **Function** | `LicenseMonitor._tick` (line 512), `run_checks` (line 163) |
| **Current code** | Background thread calls `run_checks()` which reads/writes `license_state.json` without file locking |
| **Proposed change** | Add a `threading.Lock()` around all `license_state.json` read/write operations in `_load()` and `_save()` |
| **Type** | Confirmed defect — fix |
| **Why it matters** | Race condition between background license check and startup gate could corrupt the state file. |
| **Dependencies** | None |
| **Migration risk** | None |
| **Regression risk** | Low — lock is internal, no external API change |
| **Acceptance criteria** | 1. Concurrent reads/writes to license_state.json do not corrupt the file. 2. HMAC verification still works. 3. License check interval remains 5 minutes. |
| **Safe test** | Integration test: call `_load()` and `_save()` from multiple threads simultaneously; verify no corruption |

---

### A-006: Pin Dependency Versions

| Field | Value |
|-------|-------|
| **Addresses** | SEC-007 (from full findings) |
| **File** | `requirements.txt` |
| **Current code** | `customtkinter>=5.2.2`, `Pillow>=10.0`, etc. with only lower bounds |
| **Proposed change** | Pin exact versions (e.g., `customtkinter==5.2.2`) and run `pip-audit` |
| **Type** | Recommendation — fix |
| **Why it matters** | Unpinned dependencies risk automatic installation of vulnerable future releases. |
| **Dependencies** | None |
| **Migration risk** | None |
| **Regression risk** | Low — pinned versions are known-good |
| **Acceptance criteria** | 1. All dependencies pinned to exact versions. 2. `pip-audit` reports no known vulnerabilities. 3. Application installs and runs with pinned versions. |
| **Safe test** | Create fresh venv, install pinned requirements, run test suite |

---

## Part B: Architectural Fixes (No Multi-User Enablement)

These fix correctness issues in the current architecture but do NOT make the application safe for multi-user deployment.

### B-001: Migrate Monetary Columns from REAL to INTEGER Cents

| Field | Value |
|-------|-------|
| **Addresses** | CRIT-003 |
| **Files** | `db/schema.py` (lines 56, 77, 78, 108, 121), `db/expenses.py`, `db/contracts.py`, `db/projects.py` |
| **Current code** | `expected_price REAL`, `contract_value REAL`, `paid_amount REAL`, `amount REAL`, `percentage REAL` |
| **Proposed change** | Store monetary values as integer cents (e.g., 1234567 = 12345.67 Toman). Convert at UI boundary using `decimal.Decimal`. |
| **Type** | Confirmed defect — fix (requires migration) |
| **Why it matters** | Floating-point arithmetic on monetary values produces rounding errors. For example, `0.1 + 0.2` in float is `0.30000000000000004`. Over hundreds of transactions, this accumulates. |
| **Migration risk** | HIGH — requires data migration. All existing REAL values must be converted to integer cents. Must handle values with more than 2 decimal places. Must update all calculations that sum these values. |
| **Regression risk** | HIGH — touches every financial calculation (dashboard totals, expense sums, contract values, phase prices). Must verify all totals match pre-migration values within rounding tolerance. |
| **Dependencies** | Must be done before any other financial changes. Requires comprehensive test coverage of all financial calculations. |
| **Acceptance criteria** | 1. All monetary columns are INTEGER. 2. Insert/update functions convert Decimal to cents. 3. Read functions convert cents to Decimal for display. 4. Dashboard totals match pre-migration values within 0.01 Toman. 5. All existing tests pass. 6. New tests verify no rounding drift over 1000 sequential additions. |
| **Safe test** | Migration test: create database with known REAL values, run migration, verify integer cents are correct. Calculation test: sum 1000 expenses of 0.01 Toman, verify total is exactly 10.00 Toman. |
| **Order** | Do this AFTER Phase 1 (A-001 through A-006) to avoid mixing concurrency changes with data migration |

---

### B-002: Replace Ad-Hoc DB Connections with Context Manager

| Field | Value |
|-------|-------|
| **Addresses** | HIGH-002 (downgraded to Medium) |
| **Files** | `db/projects.py`, `db/expenses.py`, `db/contracts.py`, `db/phases.py` |
| **Functions** | All `insert_*`, `update_*`, `delete_*` functions using `get_connection()` directly |
| **Current code** | `connection = get_connection(); ...; connection.commit(); connection.close()` — no try/finally |
| **Proposed change** | Replace with `with connect() as connection:` pattern used in `create_project_with_phases()` |
| **Type** | Confirmed defect (Medium) — fix |
| **Why it matters** | If an exception occurs between `get_connection()` and `connection.close()`, the connection leaks. For a desktop app this is not immediately fatal but wastes file descriptors. |
| **Migration risk** | None — no data changes |
| **Regression risk** | Medium — touches many functions; must verify all call sites handle the context manager correctly |
| **Dependencies** | None |
| **Acceptance criteria** | 1. All db write functions use `connect()` context manager. 2. No bare `get_connection()` calls remain except in read-only functions. 3. All existing tests pass. 4. Connection leak test: verify no open file descriptors after error simulation. |
| **Safe test** | Code review + run existing test suite + add test that forces an exception mid-transaction and verifies rollback |

---

### B-003: Add Date Validation Constraints

| Field | Value |
|-------|-------|
| **Addresses** | DATA-003 (from full findings) |
| **File** | `db/schema.py` |
| **Current code** | All date columns are TEXT with no format validation |
| **Proposed change** | Add CHECK constraints or triggers to validate ISO 8601 date format (YYYY-MM-DD) |
| **Type** | Recommendation — fix |
| **Why it matters** | Invalid date strings would be stored and could cause incorrect overdue calculations, trend charts, and deadline warnings. |
| **Migration risk** | Medium — existing data may contain invalid dates that would fail the new constraint |
| **Regression risk** | Low — only rejects invalid data |
| **Dependencies** | Must run `SELECT` to find existing invalid dates before adding constraint |
| **Acceptance criteria** | 1. Invalid date strings are rejected. 2. Valid dates (YYYY-MM-DD) are accepted. 3. NULL dates are allowed. 4. Existing valid data is unaffected. |
| **Safe test** | Insert invalid date, verify rejection. Insert valid date, verify acceptance. |

---

### B-004: Add Progress Range Validation

| Field | Value |
|-------|-------|
| **Addresses** | DATA-002 (from full findings) |
| **File** | `db/schema.py` (project_phases table, line 121) |
| **Current code** | `progress REAL DEFAULT 0` — no range constraint |
| **Proposed change** | Add `CHECK (progress >= 0 AND progress <= 100)` or validate in `update_project_phase()` |
| **Type** | Recommendation — fix |
| **Why it matters** | Progress values outside 0-100 would produce incorrect weighted averages in dashboard and project list. |
| **Migration risk** | Low — existing data likely within range |
| **Regression risk** | Low — only rejects invalid data |
| **Dependencies** | None |
| **Acceptance criteria** | 1. Progress = -1 is rejected. 2. Progress = 101 is rejected. 3. Progress = 50 is accepted. 4. Dashboard calculations remain correct. |
| **Safe test** | Unit test: attempt to set progress to invalid values, verify rejection |

---

## Part C: Licensing Redesign (Design Limitation)

### C-001: Replace HMAC License State with Ed25519 Signed Documents

| Field | Value |
|-------|-------|
| **Addresses** | CRIT-001, HIGH-003 |
| **Files** | `licensing/gate.py` (lines 19-28, 53-64, 67-103), `erp-license-tools/license_tools.py` |
| **Current design** | HMAC-SHA256 with hardcoded key verifies local state file against public GitHub license list |
| **Proposed change** | Issue signed license documents (Ed25519) from `erp-license-tools/`; verify locally using embedded public key; eliminate local state file forgery risk |
| **Type** | Design limitation — architectural change |
| **Why it matters** | The current design is explicitly documented as "a deterrent only" in the README. The HMAC key in source makes local state forgeable. The public GitHub list exposes all license codes. |
| **Dependencies** | `erp-license-tools/license_tools.py` already implements Ed25519 signing. The public key would be embedded in `licensing/`. Requires a license issuance workflow. |
| **Migration risk** | HIGH — all existing license codes become invalid. Users must be issued new signed licenses. |
| **Regression risk** | HIGH — affects application startup gate. Must maintain offline verification capability. |
| **Acceptance criteria** | 1. Application verifies license signature using embedded public key. 2. Forged license_state.json is rejected. 3. License codes are no longer publicly visible. 4. Offline verification works without network. 5. License expiry is enforced. 6. Existing `erp-license-tools` can issue new licenses. |
| **Safe test** | Generate a signed license, verify it is accepted. Modify the license, verify it is rejected. Tamper with the public key, verify it is rejected. |
| **Order** | This is a commercial licensing decision. Do not implement until the business model is defined. The current system is adequate as a sharing deterrent for a free/internal tool. |

---

## Part D: Multi-User Architecture (Separate Project)

These items are NOT fixes to the current application. They describe what would be required for multi-user deployment.

### D-001: Why SQLite on a Network Share Is NOT Safe

Even with WAL mode and busy_timeout (A-001), SQLite on a network share has fundamental limitations:

1. **File-level locking** — SQLite locks the entire database file for writes. Network file systems (SMB/CIFS) have unreliable locking semantics.
2. **Latency** — Each write requires network round-trip for lock acquisition.
3. **Corruption risk** — Network interruptions during write can corrupt the database file.
4. **No connection pooling** — Each client creates independent connections with no coordination.
5. **Single-writer limitation** — Only one write transaction at a time across all clients.

**Conclusion:** WAL + busy_timeout are necessary but NOT sufficient for multi-user. A client-server database (PostgreSQL) is required.

### D-002: Required Architecture for Multi-User

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Database | PostgreSQL | Multi-user, ACID, row-level locking |
| Backend API | FastAPI | Authentication, authorization, business logic |
| Frontend | Web (React/Vue) or Desktop (CustomTkinter + API client) | User interface |
| Authentication | JWT or session-based | Stateless, scalable |
| Deployment | Docker / cloud host | Centralized access |

### D-003: Foundational Changes Before Multi-User

1. **Service layer** — Extract business logic from UI into testable service functions
2. **Database abstraction** — Replace direct SQL with ORM or repository pattern
3. **Authentication service** — Centralized auth with token-based sessions
4. **Audit logging** — Centralized audit trail with user attribution
5. **API rate limiting** — Prevent abuse
6. **Data migration** — PostgreSQL schema design with proper constraints

---

## Ordered Backlog

### Phase 1: Quick Wins (1-2 days)

| Order | ID | Title | Effort | Dependencies |
|-------|----|-------|--------|--------------|
| 1 | A-003 | Remove hardcoded company data | 5 min | None |
| 2 | A-006 | Pin dependency versions | 30 min | None |
| 3 | A-001 | Add busy_timeout + WAL mode | 15 min | None |
| 4 | A-004 | Sanitize error messages | 1 hour | None |

**Acceptance:** All existing tests pass. No functional changes except improved error messages and DB resilience.

---

### Phase 2: Security Hardening (3-5 days)

| Order | ID | Title | Effort | Dependencies |
|-------|----|-------|--------|--------------|
| 5 | A-002 | Persistent brute-force lockout | 2 hours | A-001 |
| 6 | A-005 | License monitor thread safety | 2 hours | None |
| 7 | B-002 | Replace ad-hoc connections with context manager | 1 day | A-001 |

**Acceptance:** Login lockout survives restart. No connection leaks. All existing tests pass.

---

### Phase 3: Data Integrity (1-2 weeks)

| Order | ID | Title | Effort | Dependencies |
|-------|----|-------|--------|--------------|
| 8 | B-001 | Migrate monetary columns to integer cents | 3-5 days | Phase 1-2 complete, comprehensive tests |
| 9 | B-003 | Add date validation constraints | 1 day | B-001 (to avoid mixing migrations) |
| 10 | B-004 | Add progress range validation | 1 day | B-001 |

**Acceptance:** All financial calculations produce exact results. Invalid data is rejected. All tests pass including new rounding tests.

---

### Phase 4: Licensing Redesign (Timeline TBD — business decision)

| Order | ID | Title | Effort | Dependencies |
|-------|----|-------|--------|--------------|
| 11 | C-001 | Ed25519 signed license documents | 1-2 weeks | Business decision on licensing model |

**Acceptance:** License forgery is cryptographically infeasible. Offline verification works. New licenses can be issued.

---

### Phase 5: Multi-User Architecture (Separate project — 3-6 months)

| Order | ID | Title | Effort | Dependencies |
|-------|----|-------|--------|--------------|
| 12 | D-002 | Build FastAPI + PostgreSQL backend | 3-6 months | Phase 1-4 complete |
| 13 | D-003 | Develop web frontend | 2-4 months | D-002 API specification |

---

## Risk Summary

| Phase | Highest Risk | Mitigation |
|-------|-------------|------------|
| Phase 1 | WAL mode changes backup behavior | Test backup/restore after enabling WAL |
| Phase 2 | Connection refactoring breaks existing flow | Run full test suite after each function change |
| Phase 3 | Monetary migration introduces rounding errors | Compare all totals before/after migration; use Decimal for verification |
| Phase 4 | Licensing change invalidates all existing licenses | Parallel-run old and new systems during transition |
| Phase 5 | Full rewrite risks losing business logic | Extract and test service layer before rewriting |

---

## What This Plan Does NOT Do

- Does NOT enable multi-user access to the SQLite database
- Does NOT place the database on a network share
- Does NOT claim WAL + busy_timeout is sufficient for concurrent access
- Does NOT modify any source files
- Does NOT rewrite the application
- Does NOT guarantee production readiness — it is a remediation backlog

---

*End of remediation plan. All findings verified against source code on 2026-10-12.*
