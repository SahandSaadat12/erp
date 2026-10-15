# Claude implementation prompt — apply and independently review ERP stabilization fixes

You are working on an existing Python 3.12 / CustomTkinter / SQLite desktop project-management ERP. Do not merely produce an audit report. Inspect the actual repository and implement a careful, tested patch. Preserve the current UI and existing customer data wherever possible.

## Safety rules

- Work on a copy/branch. Never edit or run migrations against the only copy of a real database.
- Never print, echo, or include passwords, API keys, license codes, private keys, real customer data, or database contents in your response.
- Do not bundle `erp.db`, `.lic`, license state, private signing keys, `.git`, build/dist artifacts, demo-user scripts, or password-reset scripts in a customer release.
- Do not claim tests passed unless you actually ran them and report the exact commands/results.
- Do not rewrite the whole application. Make minimal, traceable changes and explain compatibility impacts.

## Implement and verify these items

1. **First-run administrator:** a fresh database must have no default users and must provide a first-run administrator creation flow. Require a unique username, a strong password (at least 12 characters), hash it using the existing scrypt helper, and create the account atomically with the Manager role. Existing databases with users must continue to show normal login.
2. **Authorization in the data layer:** destructive operations must reject unauthenticated calls and verify permissions inside the operation, not just in the UI. Ensure `users.manage` is required for adding/editing users or assigning roles/passwords. Whitelist archiveable tables. Cover archive, restore, permanent delete, history clearing, and entity deletion. Do not assume UI-disabled buttons are security controls.
3. **Expense validation and totals:** reject invalid/non-finite/negative amounts and invalid statuses at the database API boundary. Decide/document whether Pending expenses are costs; by default count Pending + Paid and exclude Cancelled consistently in dashboard, project, phase, and roadmap totals/charts. Add tests for totals.
4. **Remove hidden vault:** remove the hidden `C:\.erp_system\...` vault and any `attrib +h +s` calls. Permanent delete must not retain undocumented copies. If retention is needed, implement it as a documented, visible, access-controlled, backed-up feature.
5. **Backup/restore:** implement a SQLite backup API, validate `PRAGMA integrity_check` and `foreign_key_check`, create a safety backup before restore, restore via a temporary file/atomic replacement, provide a Settings UI action, and explain that the app must restart afterward. Before schema migrations that can rebuild tables, make and verify a backup; abort the migration if backup creation fails.
6. **Licensing:** inspect the exact source path used by `main.py`. Fail closed on malformed/missing `active` fields and support expiry if the current data format can safely represent it. Be honest about the constant HMAC key and public hash-list weaknesses. Do not claim client-side Python licensing is unbreakable. If changing license formats, provide a migration path and do not invalidate legitimate users silently.
7. **Build packaging:** use one authoritative PyInstaller spec/script, include CustomTkinter assets/themes and icons, and ensure output name/path match. Do not include local DB, license files/state, private keys, or default credential tools. If you cannot build/test on Windows, state that explicitly.
8. **Tests:** make the current test suite import the current implementation. Replace obsolete tests only after identifying which missing design they target; do not simply delete tests to hide failures. Add regression tests for fresh install, authorization denial, role escalation, expense validation/totals, backup/restore, migration backup, and license malformed/expired cases.

## Required deliverables

- Implemented code changes, not only recommendations.
- A concise changed-file list with the reason for each change.
- Test commands and actual pass/fail results.
- A separate list of untested areas, especially GUI/Windows/executable/network behavior.
- A remaining-risk list. Do not describe this project as ready for company-wide or multi-user deployment unless you have demonstrated that with tests.
- A clean source ZIP with secrets, local data, private keys, Git metadata, and stale executables excluded.

Review the current source carefully before applying changes. If an item is already correctly implemented, verify it and avoid duplicating it. If the current architecture makes a secure implementation impossible without a larger redesign, explain that and do not add a superficial workaround.
