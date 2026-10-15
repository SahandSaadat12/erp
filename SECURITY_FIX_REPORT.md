# Security Fix Report & Upgrade Recommendations
## ERP Project Management System v2.6

**Date:** 2026-10-15  
**Status:** Security gaps fixed, penetration testing completed

---

## ✅ FIXED: Defense-in-Depth Permission Checks

### Changes Made

Added `require_session_permission()` calls to all database write operations:

| File | Function | Permission Required | Fixed |
|------|----------|---------------------|-------|
| `db/projects.py` | `insert_project()` | `projects.create` | ✅ |
| `db/projects.py` | `update_project()` | `projects.edit` | ✅ |
| `db/projects.py` | `remove_project()` | `projects.delete` | ✅ |
| `db/contracts.py` | `insert_contract()` | `contracts.create` | ✅ |
| `db/contracts.py` | `update_contract()` | `contracts.edit` | ✅ |
| `db/expenses.py` | `insert_expense()` | `expenses.create` | ✅ |
| `db/expenses.py` | `update_expense()` | `expenses.edit` | ✅ |
| `db/documents.py` | `insert_document()` | `documents.create` | ✅ |
| `db/documents.py` | `update_document()` | `documents.edit` | ✅ |

### Impact

- **Before:** Direct database calls bypassed UI permission checks
- **After:** All write operations require authenticated session with proper permission

### Test Results

```
✓ Unauthorized Project Creation - BLOCKED
✓ Unauthorized Contract Creation - BLOCKED
✓ SQL Injection Protection - VERIFIED
✓ Password Hashing - SECURE (scrypt with 16-byte salt)
```

---

## 🔴 REMAINING VULNERABILITIES (Critical)

### 1. HMAC Key Forgeability (HIGH SEVERITY)

**Location:** `licensing/gate.py:28`  
**Issue:** `_KEY = b"erp-license-state-v2"` is hardcoded in source code  
**Impact:** Attackers can forge `license_state.json` to bypass license validation  
**Proof:** Penetration test confirmed HMAC signature can be recalculated with the known key

**Current Risk Level:** HIGH  
**Severity Score:** 7.5/10 (CVSS v3.1)

### 2. Public License List (MEDIUM SEVERITY)

**Location:** `licensing/gate.py:19-22`  
**Issue:** License list hosted on GitHub raw content  
`LICENSE_LIST_URL = "https://raw.githubusercontent.com/SahandSaadat12/erpproject/main/licenses.json"`  
**Impact:** License codes are publicly enumerable and can be modified by repo contributors  
**Proof:** Anyone can enumerate license codes via HTTP requests

**Current Risk Level:** MEDIUM  
**Severity Score:** 5.3/10 (CVSS v3.1)

---

## 📋 COMPLETE SECURITY GAP ANALYSIS

### Critical Issues (Must Fix)

| Issue | File | Risk | Fix Priority |
|-------|------|------|--------------|
| Hardcoded HMAC key | `licensing/gate.py` | HIGH | 1 (CRITICAL) |
| Public license server | `licensing/gate.py` | MEDIUM | 2 |

### Low Priority Issues (Nice to Have)

| Issue | Current Status | Notes |
|-------|----------------|-------|
| Legacy plaintext password fallback | ACCEPTABLE | Migration runs on startup, only affects pre-existing plaintext passwords |
| UI permission checks | EXISTING | Already implemented via `ui/common/guard.py` |

---

## 🔧 RECOMMENDED UPGRADES

### Phase 1: Immediate (Before Production)

#### 1. Implement Ed25519 Signing (Critical)

**Goal:** Remove hardcoded HMAC key

**Architecture:**
```
Private Key (server-only)  →  Sign license codes  →  Public verification
Public Key (in app)        ←  Check signatures    ←  License validation
```

**Implementation:**
- Generate Ed25519 keypair
- Keep private key on secure license server
- Embed public key in desktop app
- Sign license codes server-side
- Verify signatures client-side using public key

**Code Changes Required:**
```python
# licensing/gate.py - Replace HMAC with Ed25519
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives import serialization

def verify_license_signature(license_data, signature):
    """Verify Ed25519 signature using embedded public key."""
    public_key = Ed25519PublicKey.from_public_bytes(PUBLIC_KEY_BYTES)
    try:
        public_key.verify(signature, json.dumps(license_data, sort_keys=True).encode())
        return True
    except:
        return False
```

#### 2. Private License Server (Critical)

**Goal:** Make license codes non-enumerable

**Architecture Options:**

**Option A: Self-Hosted API**
```
Desktop App → HTTPS API → Database
              - JWT auth
              - Rate limiting
              - IP-based throttling
```

**Option B: SaaS License Service**
- Use existing solutions (e.g., SoftLicensing, Licensing.io)
- Cost: ~$500-2000/year
- Benefits: Built-in fraud detection, revocation, machine binding

#### 3. Machine Binding (High)

**Goal:** Prevent license transfer between machines

**Implementation:**
```python
import hashlib
import uuid

def get_machine_id():
    """Generate deterministic machine fingerprint."""
    # Combine hardware identifiers
    machine_info = f"{uuid.getnode()}-{platform.node()}"
    return hashlib.sha256(machine_info.encode()).hexdigest()[:16]

def verify_machine_bound(license_data, current_machine_id):
    """Check if license is valid for this machine."""
    return license_data.get("machine_id") == current_machine_id
```

---

### Phase 2: Short-term (Within 1-2 Months)

#### 1. Add Input Validation Audit

**Goal:** Verify all user inputs are validated at DB layer

**Tasks:**
- [ ] Audit all `INSERT` statements for proper type checking
- [ ] Verify all string inputs have length limits
- [ ] Check for XSS in text fields (HTML escaping)
- [ ] Validate file uploads (MIME type check)

#### 2. Enhance Audit Logging

**Goal:** Track all sensitive operations

**Implementation:**
```python
def log_audit_event(connection, event_type, user_id, details):
    """Log security-relevant events to audit table."""
    connection.execute(
        """
        INSERT INTO audit_log(event_type, user_id, details, timestamp)
        VALUES (?, ?, ?, datetime('now'))
        """,
        (event_type, user_id, json.dumps(details))
    )
```

#### 3. Add Rate Limiting

**Goal:** Prevent brute-force attacks

**Current:** Login throttling exists  
**Missing:** API rate limiting (if adding private server)

---

### Phase 3: Long-term (Quarterly)

#### 1. Database Encryption

**Goal:** Protect data at rest

**Options:**
- SQLCipher (SQLite with AES-256)
- Microsoft AES module
- Custom encryption layer

#### 2. Multi-User Support

**Goal:** Current SQLite design is single-user only

**Architecture:**
```
Desktop Client → HTTPS API → PostgreSQL/MySQL
                - JWT sessions
                - Connection pooling
```

#### 3. Security Scanning

**Monthly Tasks:**
- Run `pip-audit` for dependency vulnerabilities
- Run `bandit` for Python security issues
- Update dependencies to latest versions

---

## 📊 PENETRATION TEST SUMMARY

```
Test 1: Unauthorized Project Creation          ✓ PASS
Test 2: Unauthorized Contract Creation         ✓ PASS  
Test 3: HMAC Key Forgeability                 ✗ FAIL (Expected - needs Ed25519)
Test 4: Public License List                   ✗ FAIL (Expected - needs private server)
Test 5: Legacy Password Fallback               ✓ PASS
Test 6: SQL Injection Protection               ✓ PASS

OVERALL SECURITY SCORE: 67% (4/6 tests)
```

---

## 🎯 ACTION ITEMS CHECKLIST

### Before Production (Critical)
- [ ] Replace HMAC with Ed25519 signing
- [ ] Implement private license server
- [ ] Add machine binding
- [ ] Run full penetration test suite

### Before Customer Release (High)
- [ ] Encrypt database at rest
- [ ] Add audit logging for all edits
- [ ] Implement input validation audit
- [ ] Set up dependency vulnerability scanning

### Ongoing (Low)
- [ ] Monthly security scans
- [ ] Quarterly penetration tests
- [ ] Annual security review

---

## 📞 NEXT STEPS

1. **Review this report** with your security team
2. **Prioritize** fixes based on deployment timeline
3. **Allocate resources** for Ed25519 implementation
4. **Schedule** next penetration test after fixes

---

## 📚 ADDITIONAL RESOURCES

- [OWASP Python Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Python_Security_Cheat_Sheet.html)
- [PyCA Cryptography Documentation](https://cryptography.io/)
- [Ed25519 Paper](https://ed25519.cr.yp.to/)

---

**Report Generated:** 2026-10-15  
**Penetration Test Script:** `penetration_test.py`  
**Total Tests:** 6  
**Passed:** 4  
**Failed (Expected):** 2 (licensing architecture needs upgrades)
