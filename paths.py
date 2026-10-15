"""
Single source of truth for every file / folder path used by the app.

* Running from source  -> data lives next to the code (same as before).
* Running as .exe      -> data lives in  %APPDATA%\\ERP-ProjectManagement
                          (the exe folder may be read-only, and a relative
                          "erp.db" would silently create an empty database
                          wherever the exe was launched from).
"""

import os
import sys

APP_NAME = "ERP-ProjectManagement"

FROZEN = bool(getattr(sys, "frozen", False))

if FROZEN:
    RESOURCE_DIR = getattr(
        sys, "_MEIPASS", os.path.dirname(sys.executable)
    )
    DATA_DIR = os.path.join(
        os.environ.get("APPDATA", os.path.expanduser("~")),
        APP_NAME
    )
else:
    RESOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = RESOURCE_DIR

BACKUP_DIR = os.path.join(DATA_DIR, "backups")
DOCUMENTS_DIR = os.path.join(DATA_DIR, "documents")

DB_PATH = os.path.join(DATA_DIR, "erp.db")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

ICON_DIR = os.path.join(RESOURCE_DIR, "icons")

for _folder in (DATA_DIR, BACKUP_DIR, DOCUMENTS_DIR):
    try:
        os.makedirs(_folder, exist_ok=True)
    except OSError:
        pass


def resource_path(*parts):
    """Path to a read-only bundled resource (icons, ...)."""
    return os.path.join(RESOURCE_DIR, *parts)

# ---- licensing (see licensing/) ----
LICENSE_FILE = os.path.join(DATA_DIR, "license.lic")
LICENSE_STATE_FILE = os.path.join(DATA_DIR, "license_state.json")
