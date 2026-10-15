"""Password hashing (scrypt, standard library only)."""

import base64
import hashlib
import hmac
import os

_PREFIX = "scrypt$"
_N, _R, _P = 2 ** 14, 8, 1


def is_hashed(value):
    return isinstance(value, str) and value.startswith(_PREFIX)


def hash_password(password):
    salt = os.urandom(16)

    digest = hashlib.scrypt(
        str(password).encode("utf-8"),
        salt=salt, n=_N, r=_R, p=_P
    )

    return (
        _PREFIX
        + base64.b64encode(salt).decode()
        + "$"
        + base64.b64encode(digest).decode()
    )


def verify_password(password, stored):
    if not is_hashed(stored):
        # legacy plain-text value
        return hmac.compare_digest(str(password), str(stored or ""))

    try:
        _, salt_b64, digest_b64 = stored.split("$")
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)

        digest = hashlib.scrypt(
            str(password).encode("utf-8"),
            salt=salt, n=_N, r=_R, p=_P
        )

        return hmac.compare_digest(digest, expected)

    except Exception:
        return False
