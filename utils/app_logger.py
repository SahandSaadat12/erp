"""Safe application logging — writes diagnostic details to a local log file.

Never logs passwords, license secrets, authentication tokens, or personal
information.  Logging failures are silently swallowed so they can never
crash the application.
"""

import os
import traceback
from datetime import datetime
from paths import DATA_DIR

_LOG_FILE = os.path.join(DATA_DIR, "app.log")
_MAX_BYTES = 1_000_000


def _rotate():
    try:
        if os.path.exists(_LOG_FILE) and os.path.getsize(_LOG_FILE) > _MAX_BYTES:
            os.replace(_LOG_FILE, _LOG_FILE + ".1")
    except Exception:
        pass


def _write(level, message):
    try:
        _rotate()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {level} {message}\n")
    except Exception:
        pass


def info(message):
    _write("INFO", str(message))


def warning(message):
    _write("WARN", str(message))


def error(message, exc_info=False):
    text = str(message)
    if exc_info:
        text += "\n" + traceback.format_exc()
    _write("ERROR", text)
