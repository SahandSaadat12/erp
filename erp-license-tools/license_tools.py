#!/usr/bin/env python3
"""
ERP developer license tool (CLI).   *** KEEP THIS FOLDER OUT OF THE ERP PROJECT / GIT REPO ***

Holds the two PRIVATE Ed25519 keys:
    keys/license_signing_private.pem   signs license files
    keys/status_signing_private.pem    signs revocation-status documents
(override the folder with ERP_LICENSE_KEY_DIR; optional passphrase protection via
 ERP_KEY_PASSPHRASE).  The ERP receives only the two PUBLIC keys.

Commands
  init-keys   [--write-public-keys PATH_TO/licensing/public_keys.py] [--force]
  issue       --machine-id M1-.. --customer NAME --expires YYYY-MM-DD
              --features projects,contracts,... [--license-id ID] [--status-url https://..]
              [--out FILE]
  revoke / reinstate --license-id ID        (then run publish)
  publish     --out-dir DIR [--valid-days 7]   writes <license_id>.json for every license
  list
  verify      --license FILE
"""

import argparse
import base64
import json
import os
import re
import secrets
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

HERE = Path(__file__).resolve().parent
KEY_DIR = Path(os.environ.get("ERP_LICENSE_KEY_DIR", HERE / "keys"))
DATA_DIR = Path(os.environ.get("ERP_LICENSE_DATA_DIR", HERE / "data"))
REGISTRY = DATA_DIR / "registry.json"

LICENSE_PRIV = "license_signing_private.pem"
LICENSE_PUB = "license_signing_public.pem"
STATUS_PRIV = "status_signing_private.pem"
STATUS_PUB = "status_signing_public.pem"

# must match the ERP's licensing/verifier.py and revocation.py
LICENSE_SIG_PREFIX = b"ERP-LICENSE-SIG-V1\x00"
STATUS_SIG_PREFIX = b"ERP-STATUS-SIG-V1\x00"
KNOWN_FEATURES = ("projects", "contracts", "expenses", "documents", "roadmap", "excel_export")
MACHINE_ID_RE = re.compile(r"^M1-(?:[0-9A-F]{4}-){7}[0-9A-F]{4}$")
LICENSE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{5,63}$")


# ---------------------------------------------------------------- canonical
def canonical_dumps(obj):
    def check(v):
        if v is None or isinstance(v, (bool, str, int)):
            return
        if isinstance(v, float):
            raise ValueError("floats are not allowed in signed payloads")
        if isinstance(v, (list, tuple)):
            for i in v:
                check(i)
        elif isinstance(v, dict):
            for k, i in v.items():
                if not isinstance(k, str):
                    raise ValueError("keys must be strings")
                check(i)
        else:
            raise ValueError(f"unsupported type {type(v).__name__}")
    check(obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def fmt(moment):
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_utc():
    return datetime.now(timezone.utc).replace(microsecond=0)


# ---------------------------------------------------------------- keys
def _passphrase():
    value = os.environ.get("ERP_KEY_PASSPHRASE")
    return value.encode() if value else None


def _write_private(path, key):
    pw = _passphrase()
    enc = (serialization.BestAvailableEncryption(pw) if pw else serialization.NoEncryption())
    path.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                                       serialization.PrivateFormat.PKCS8, enc))
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _pub_b64(key):
    raw = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return base64.b64encode(raw).decode()


def load_private(name):
    path = KEY_DIR / name
    if not path.exists():
        sys.exit(f"missing key {path} - run: init-keys")
    return serialization.load_pem_private_key(path.read_bytes(), password=_passphrase())


def cmd_init_keys(args):
    KEY_DIR.mkdir(parents=True, exist_ok=True)
    if (KEY_DIR / LICENSE_PRIV).exists() and not args.force:
        sys.exit(f"keys already exist in {KEY_DIR}; use --force to replace "
                 "(this INVALIDATES every license issued so far)")
    out = {}
    for priv, pub, label in ((LICENSE_PRIV, LICENSE_PUB, "license"), (STATUS_PRIV, STATUS_PUB, "status")):
        key = Ed25519PrivateKey.generate()
        _write_private(KEY_DIR / priv, key)
        (KEY_DIR / pub).write_bytes(key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
        out[label] = _pub_b64(key)
    print("Private keys written to:", KEY_DIR, "(BACK THEM UP; never copy into the ERP)")
    print("LICENSE_PUBLIC_KEY_B64 =", json.dumps(out["license"]))
    print("STATUS_PUBLIC_KEY_B64  =", json.dumps(out["status"]))
    if args.write_public_keys:
        target = Path(args.write_public_keys)
        if target.name != "public_keys.py":
            sys.exit("--write-public-keys must point to licensing/public_keys.py")
        text = target.read_text(encoding="utf-8")
        for name, value in (("LICENSE_PUBLIC_KEY_B64", out["license"]),
                            ("STATUS_PUBLIC_KEY_B64", out["status"])):
            text, n = re.subn(rf'^{name} = ".*"$', f'{name} = "{value}"', text, flags=re.M)
            if n != 1:
                sys.exit(f"could not update {name} in {target}")
        target.write_text(text, encoding="utf-8")
        print("Updated public keys in", target)


# ---------------------------------------------------------------- registry
def load_registry():
    if REGISTRY.exists():
        return json.loads(REGISTRY.read_text(encoding="utf-8"))
    return {"licenses": {}}


def save_registry(reg):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps(reg, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


# ---------------------------------------------------------------- issue
def build_license(key, *, machine_id, customer, expires, features, license_id=None,
                  status_url=None, issued_at=None):
    machine_id = machine_id.strip().upper()
    if not MACHINE_ID_RE.match(machine_id):
        raise ValueError("invalid Machine ID format (expected M1-XXXX-... 8 groups)")
    if not customer.strip():
        raise ValueError("customer is required")
    features = [f.strip() for f in features if f.strip()]
    if len(set(features)) != len(features) or any(f not in KNOWN_FEATURES for f in features):
        raise ValueError(f"features must be unique and from {KNOWN_FEATURES}")
    license_id = license_id or ("LIC-" + secrets.token_hex(6).upper())
    if not LICENSE_ID_RE.match(license_id):
        raise ValueError("invalid license id")
    issued = issued_at or now_utc()
    expires_dt = (datetime.strptime(expires, "%Y-%m-%d") + timedelta(hours=23, minutes=59, seconds=59)
                  ).replace(tzinfo=timezone.utc)
    if expires_dt <= issued:
        raise ValueError("expiration must be in the future")
    payload = {"version": 1, "license_id": license_id, "machine_id": machine_id,
               "customer": customer.strip(), "issued_at": fmt(issued),
               "expires_at": fmt(expires_dt), "features": sorted(features)}
    if status_url:
        if not status_url.startswith("https://"):
            raise ValueError("status_url must be https")
        payload["status_url"] = status_url
    sig = key.sign(LICENSE_SIG_PREFIX + canonical_dumps(payload))
    return {"payload": payload, "signature": base64.b64encode(sig).decode()}


def cmd_issue(args):
    key = load_private(LICENSE_PRIV)
    lic = build_license(key, machine_id=args.machine_id, customer=args.customer,
                        expires=args.expires, features=args.features.split(","),
                        license_id=args.license_id, status_url=args.status_url)
    p = lic["payload"]
    out = Path(args.out or f"{p['license_id']}.lic")
    out.write_text(json.dumps(lic, indent=2, ensure_ascii=False), encoding="utf-8")
    reg = load_registry()
    if p["license_id"] in reg["licenses"]:
        sys.exit("license id already exists in registry")
    reg["licenses"][p["license_id"]] = {
        "customer": p["customer"], "machine_id": p["machine_id"], "expires_at": p["expires_at"],
        "features": p["features"], "status": "active", "sequence": 0, "status_url": p.get("status_url", "")}
    save_registry(reg)
    print("License written:", out, "| id:", p["license_id"])


# ---------------------------------------------------------------- revocation
def set_status(license_id, status):
    reg = load_registry()
    if license_id not in reg["licenses"]:
        sys.exit("unknown license id")
    reg["licenses"][license_id]["status"] = status
    save_registry(reg)
    print(f"{license_id} -> {status}. Run 'publish' and upload the files.")


def sign_status(key, license_id, status, sequence, signed_at, valid_until):
    payload = {"version": 1, "license_id": license_id, "status": status,
               "signed_at": fmt(signed_at), "valid_until": fmt(valid_until), "sequence": sequence}
    sig = key.sign(STATUS_SIG_PREFIX + canonical_dumps(payload))
    return {"payload": payload, "signature": base64.b64encode(sig).decode()}


def cmd_publish(args):
    key = load_private(STATUS_PRIV)
    reg = load_registry()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    now = now_utc()
    for lid, info in reg["licenses"].items():
        seq = max(int(info.get("sequence", 0)) + 1, int(time.time()))   # strictly increasing
        doc = sign_status(key, lid, info["status"], seq, now, now + timedelta(days=args.valid_days))
        (out / f"{lid}.json").write_text(json.dumps(doc, indent=2), encoding="utf-8")
        info["sequence"] = seq
    save_registry(reg)
    print(f"Published {len(reg['licenses'])} status file(s) to {out} - upload them to the HTTPS host.")


def cmd_list(_args):
    for lid, i in sorted(load_registry()["licenses"].items()):
        print(f"{lid}  {i['status']:8}  {i['customer']}  expires {i['expires_at']}  {i['machine_id']}")


def cmd_verify(args):
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    env = json.loads(Path(args.license).read_text(encoding="utf-8"))
    pub = load_pem_public_key((KEY_DIR / LICENSE_PUB).read_bytes())
    pub.verify(base64.b64decode(env["signature"], validate=True),
               LICENSE_SIG_PREFIX + canonical_dumps(env["payload"]))
    print("signature OK:", json.dumps(env["payload"], ensure_ascii=False))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("init-keys"); a.add_argument("--write-public-keys"); a.add_argument("--force", action="store_true")
    a.set_defaults(fn=cmd_init_keys)
    a = sub.add_parser("issue")
    for n in ("machine-id", "customer", "expires", "features"):
        a.add_argument("--" + n, required=True)
    for n in ("license-id", "status-url", "out"):
        a.add_argument("--" + n)
    a.set_defaults(fn=cmd_issue)
    for n, st in (("revoke", "revoked"), ("reinstate", "active")):
        a = sub.add_parser(n); a.add_argument("--license-id", required=True)
        a.set_defaults(fn=lambda x, st=st: set_status(x.license_id, st))
    a = sub.add_parser("publish"); a.add_argument("--out-dir", required=True)
    a.add_argument("--valid-days", type=int, default=7); a.set_defaults(fn=cmd_publish)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    a = sub.add_parser("verify"); a.add_argument("--license", required=True); a.set_defaults(fn=cmd_verify)
    args = p.parse_args(argv)
    try:
        args.fn(args)
    except ValueError as error:
        sys.exit(f"error: {error}")


if __name__ == "__main__":
    main()
