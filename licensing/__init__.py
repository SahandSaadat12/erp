"""
Offline-first, machine-bound licensing for the ERP.

Trust boundary: this package only ever holds PUBLIC verification keys
(public_keys.py).  The private signing keys live in the developer's
separate license-tools folder and are never shipped.

This package is deliberately independent of the business database
(no import of db/, database.py, auth, ...).
"""
