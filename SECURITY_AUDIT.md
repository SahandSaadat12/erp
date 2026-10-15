# Security Audit Report

**Date:** 2026-10-12  
**Scope:** Source-based security assessment of ERP Project Management desktop application  
**Tests:** 55 passed (38 existing + 17 new security tests)

---

## Confirmed Findings

### SEC-001: Hardcoded HMAC Key in License State

| Field | Value |
|-------|-------|
| **Severity** | High |
| **File** | `licensing/gate.py:28` |
| **Evidence** | `_KEY = b"erp-license-state-v2"` — constant in source |
| **Impact** | Anyone with source access can forge `license_state.json` with valid HMAC, bypassing license checks |
| **Fix** | Architectural redesign required (Ed25519). Not fixed in this session. |
| **Residual Risk** | License state is forgeable by a determined attacker |

### SEC-002: Public GitHub License List

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **File** | `licensing/gate.py:19-22` |
| **Evidence** | `LICENSE_LIST_URL` points to public GitHub raw content |
| **Impact** | License codes are publicly enumerable; license list can be modified by repo contributors |
| **Fix** | Requires private license server. Not fixed in this session. |
| **Residual Risk** | Licensing is a deterrent only |

### SEC-003: Legacy Plaintext Password Verification

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **File** | `security.py:33-35` |
| **Evidence** | `verify_password()` falls back to `hmac.compare_digest(str(password), str(stored))` for non-scrypt values |
| **Impact** | If any user has a plaintext password in the DB, it is directly comparable. Migration exists in `db/migrations.py:_hash_legacy_passwords()` which runs on startup. |
| **Fix** | Migration already exists and runs automatically. No code change needed. |
| **Residual Risk** | Low — migration hashes legacy passwords on next startup |

### SEC-004: Missing Permission Check on `remove_project`

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **File** | `db/projects.py:349-368` |
| **Evidence** | `remove_project()` performs DELETE without calling `require_session_permission()` |
| **Impact** | If called directly (bypassing UI), no permission check occurs. UI does check via `guarded_delete()`. |
| **Fix** | Add `require_session_permission()` call. See regression test. |
| **Residual Risk** | Low for desktop app (UI enforces), but defense-in-depth gap |

### SEC-005: Missing Permission Check on `insert_document` / `update_document`

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **File** | `db/documents.py:196, 323` |
| **Evidence** | Neither function calls `require_session_permission()` |
| **Impact** | Direct DB calls bypass authorization. UI enforces via `perm_state()`. |
| **Fix** | Add permission checks. See regression test. |
| **Residual Risk** | Low for desktop app |

### SEC-006: Missing Permission Check on `insert_contract` / `update_contract`

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **File** | `db/contracts.py:279, 341` |
| **Evidence** | Neither function calls `require_session_permission()` |
| **Impact** | Direct DB calls bypass authorization. UI enforces via `guarded()`. |
| **Fix** | Add permission checks. See regression test. |
| **Residual Risk** | Low for desktop app |

### SEC-007: Missing Permission Check on `insert_expense` / `update_expense`

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **File** | `db/expenses.py:137, 416` |
| **Evidence** | Neither function calls `require_session_permission()` |
| **Impact** | Direct DB calls bypass authorization. UI enforces via `guarded()`. |
| **Fix** | Add permission checks. See regression test. |
| **Residual Risk** | Low for desktop app |

### SEC-008: Missing Permission Check on `insert_project` / `update_project`

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **File** | `db/projects.py:10, 226` |
| **Evidence** | Neither function calls `require_session_permission()` |
| **Impact** | Direct DB calls bypass authorization. UI enforces via `guarded()`. |
| **Fix** | Add permission checks. See regression test. |
| **Residual Risk** | Low for desktop app |

---

## Areas With No Confirmed Vulnerabilities

| Area | Status | Notes |
|------|--------|-------|
| SQL Injection | PASS | All queries use parameterized statements. Table names in archive.py use `quote_identifier()`. |
| Password Hashing | PASS | scrypt with 16-byte salt, N=2^14, r=8, p=1 |
| Session Isolation | PASS | Single-session design via `session_context` table with `CHECK (id = 1)` |
| Brute-Force Protection | PASS | Persistent lockout via `session_context.failed_attempts` and `locked_until` |
| File Extension Validation | PASS | `open_document.py` validates against `ALLOWED_EXTENSIONS` whitelist |
| Error Message Exposure | PASS | User-facing messages are generic; details logged to `app.log` |
| Dependency Pinning | PASS | All 5 dependencies pinned to exact tested versions |
| Foreign Key Enforcement | PASS | `PRAGMA foreign_keys = ON` on every connection |
| Connection Cleanup | PASS | All write functions use `try/finally: connection.close()` |
| License State Thread Safety | PASS | `_state_lock` protects `_load()` and `_save()` |

---

## Summary

| Severity | Count | Fixed | Architectural |
|----------|-------|-------|---------------|
| High | 1 | 0 | 1 (SEC-001) |
| Medium | 7 | 0 | 0 |
| Low | 0 | 0 | 0 |

**Note:** SEC-004 through SEC-008 are defense-in-depth gaps. The UI enforces permissions correctly. These would become Critical if the database were exposed directly (e.g., via a future API layer). They are documented here for completeness.

---

*End of security audit report.*
