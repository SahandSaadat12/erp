# Security Test Plan

## Automated Tests

### Authentication
- `test_password_hashing_uses_scrypt` — verifies scrypt prefix
- `test_password_verification_correct` — correct password accepted
- `test_password_verification_incorrect` — wrong password rejected
- `test_legacy_plaintext_password_verification` — legacy fallback works

### Authorization
- `test_require_session_permission_no_session` — no session = denied
- `test_require_session_permission_active_session` — active session = allowed
- `test_disabled_user_denied` — disabled account = denied
- `test_manager_has_all_permissions` — Manager role has full access

### Database Integrity
- `test_foreign_keys_enforced` — FK violations rejected
- `test_parameterized_query_prevents_injection` — queries use parameters

### File Operations
- `test_document_open_validates_extension` — .exe/.bat blocked
- `test_app_logger_does_not_expose_secrets` — no secrets in logs

### Licensing
- `test_state_lock_exists` — thread lock present
- `test_load_returns_none_for_missing_file` — graceful handling
- `test_save_and_load_roundtrip` — atomic write works
- `test_hmac_key_is_constant` — key is hardcoded (documented risk)

## Manual Tests (Not Automated)

| Test | Method | Expected |
|------|--------|----------|
| Login lockout persistence | 5 failed logins, restart app | Lockout survives restart |
| License offline behavior | Disconnect internet, start app | 14-day grace period |
| Backup/restore | Create backup, restore to temp | Data preserved |
| GUI permission enforcement | Login as Engineer, try delete | Button disabled |
| First-run admin creation | Empty DB, create admin | Works once, then login |

## Run Command

```powershell
python -m unittest discover -v
```

## Coverage

- 55 automated tests covering auth, authorization, DB integrity, file ops, licensing
- GUI runtime: NOT TESTED (no display)
- Windows-specific: NOT TESTED
- Network licensing: NOT TESTED (no external calls)
- Concurrent access: Partially tested (license state lock)
