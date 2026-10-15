# Audit-fix notes

This is a targeted stabilization pass based on the source and the independent review report. It is **not** a declaration that the ERP is production-ready.

## Changed in this pass

1. Fresh databases no longer need hardcoded demo credentials; the login screen offers first-run administrator creation (minimum 12-character password).
2. Added database-layer permission checks for destructive operations and archive/purge actions; user-management writes require `users.manage` rather than only list-management access.
3. Added expense amount/status validation. Invalid text, negative amounts, NaN/infinity, and unknown statuses are rejected. Cost totals and expense charts exclude `Cancelled`; `Pending` and `Paid` remain included.
4. Removed the hidden `C:\\.erp_system\\...` vault and its hidden/system-attribute file writes. Permanent deletion now purges the archive record without creating an undisclosed copy.
5. Added verified SQLite backup/restore helpers. Restore validates the backup and current DB, creates a safety backup, restores through a temporary file, then atomically replaces the database. Settings now exposes restore.
6. Existing databases with a schema version below the current version are backed up and checked before migration; migration stops if a verified backup cannot be created.
7. The simple GitHub license gate now fails closed if an `active` flag is missing/invalid and supports an optional `expires: YYYY-MM-DD` field. This does **not** fix the fundamental forgeable local HMAC state or public hash-list design.
8. Updated the PyInstaller spec to collect CustomTkinter/PersianTools data and icons, and made the batch file build from that one spec.
9. Replaced tests that targeted a missing, abandoned licensing implementation with tests for the actual source design and the fixes above.
10. Removed default-credential scripts, the live database, license files/state, private signing keys, Git metadata, and old build artifacts from this shareable ZIP.

## Known limitations / not completed

- The GUI was not launched in this environment. First-run login, Settings restore button, and packaging must be smoke-tested on Windows.
- The PyInstaller executable was not rebuilt here; PyInstaller/Windows runtime testing is still required.
- Licensing remains a deterrent only: a constant local HMAC key and public license hashes make local state forgeable. Do not promise strong tamper resistance or machine binding.
- Full accounting/invoice/payment support is absent; dashboard expected project value is not collected revenue.
- SQLite remains single-PC/single-active-user only.
- All UI forms, every DB operation, migration from every historical schema, and every report have not been audited.
