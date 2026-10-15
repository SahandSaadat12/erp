
"""Simple GitHub-code license gate."""
import hashlib
import hmac
import json
import os
import queue
import tempfile
import threading
import time
import urllib.request

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from . import messages_fa


LICENSE_LIST_URL = (
    "https://raw.githubusercontent.com/"
    "SahandSaadat12/erpproject/main/licenses.json"
)

OFFLINE_GRACE_DAYS = 14
CHECK_INTERVAL = timedelta(hours=6)
MAX_JUMP = timedelta(days=30)

_KEY = b"erp-license-state-v2"
_active = {"license": None}
_state_lock = threading.Lock()


@dataclass(frozen=True)
class GateResult:
    ok: bool
    code: str = "OK"
    days_left: int = 0


def _now():
    return datetime.now(timezone.utc)


def _iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse(s):
    return datetime.strptime(
        s, "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=timezone.utc)


def hash_code(code):
    return hashlib.sha256(
        ("ERP-LIC-V2:" + code.strip().upper()).encode()
    ).hexdigest()


def _mac(d):
    return hmac.new(
        _KEY,
        json.dumps(d, sort_keys=True).encode(),
        hashlib.sha256
    ).hexdigest()


def _load(path):
    with _state_lock:
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)

            if hmac.compare_digest(
                raw["mac"],
                _mac(raw["data"])
            ):
                return raw["data"]

        except Exception:
            pass

        return None


def _save(path, d):
    with _state_lock:
        try:
            fd, tmp = tempfile.mkstemp(
                dir=os.path.dirname(path) or ".",
                suffix=".tmp"
            )

            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "data": d,
                        "mac": _mac(d)
                    },
                    f
                )

            os.replace(tmp, path)

        except OSError:
            pass


def fetch_list(url=LICENSE_LIST_URL, timeout=5):
    if not url.lower().startswith("https://"):
        raise ValueError("https only")

    req = urllib.request.Request(
        f"{url}?t={int(time.time())}",
        headers={
            "User-Agent": "ERP-License/2",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
    )

    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(256 * 1024).decode("utf-8")


def _verify(code_hash, fetcher, now=None):
    """
    Returns:
        "ok"      -> license exists and is active
        "denied"  -> license exists but is inactive / invalid
        None      -> network or JSON problem
    """

    try:
        entries = json.loads(fetcher())["licenses"]

        if not isinstance(entries, dict):
            return None

    except Exception:
        return None

    e = entries.get(code_hash)

    if not isinstance(e, dict):
        return "denied"

    # Fail closed: a license entry must explicitly be active.
    if e.get("active") is not True:
        return "denied"

    # Optional UTC expiry field (YYYY-MM-DD). Invalid expiry is rejected.
    expires = e.get("expires")
    if expires is not None:
        try:
            expiry_day = datetime.strptime(str(expires), "%Y-%m-%d").date()
        except (TypeError, ValueError):
            return "denied"
        check_time = now or _now()
        if check_time.date() > expiry_day:
            return "denied"

    return "ok"


def run_checks(
    code=None,
    now=None,
    force=False,
    fetcher=fetch_list,
    state_path=None
):
    try:
        if state_path is None:
            from paths import LICENSE_STATE_FILE
            state_path = LICENSE_STATE_FILE

        now = now or _now()
        st = _load(state_path)

        # ---------------------------------------------------------
        # NEW CODE
        # ---------------------------------------------------------
        # Whenever a code is explicitly supplied, verify THAT code.
        # This allows replacing an inactive/expired license.
        # ---------------------------------------------------------
        if code:
            h = hash_code(code)

            res = _verify(h, fetcher, now)

            if res is None:
                return GateResult(False, "NEED_INTERNET")

            if res == "denied":
                return GateResult(False, "INVALID_CODE")

            t = _iso(now)

            _save(
                state_path,
                {
                    "code_hash": h,
                    "last_ok": t,
                    "last_attempt": t,
                    "high_water": t,
                    "disabled": False,
                }
            )

            return GateResult(
                True,
                "OK",
                OFFLINE_GRACE_DAYS
            )

        # ---------------------------------------------------------
        # FIRST RUN
        # ---------------------------------------------------------
        if st is None:
            return GateResult(False, "NEED_CODE")

        # ---------------------------------------------------------
        # EXISTING LICENSE
        # ---------------------------------------------------------
        hw = _parse(st["high_water"])

        # Prevent clock rollback from extending grace period.
        eff = max(now, hw)

        last_ok = _parse(st["last_ok"])

        grace = timedelta(
            days=OFFLINE_GRACE_DAYS
        )

        due = (
            force
            or st["disabled"]
            or eff - last_ok > grace
            or eff - _parse(st["last_attempt"])
            >= CHECK_INTERVAL
        )

        if due:
            st["last_attempt"] = _iso(eff)

            res = _verify(
                st["code_hash"],
                fetcher,
                now,
            )

            if res == "ok":
                st["last_ok"] = _iso(eff)
                st["disabled"] = False
                last_ok = eff

            elif res == "denied":
                st["disabled"] = True

            # res is None:
            # keep previous disabled state and use offline grace.

        if hw < now <= hw + MAX_JUMP:
            st["high_water"] = _iso(now)

        _save(state_path, st)

        # ---------------------------------------------------------
        # LICENSE DISABLED
        # ---------------------------------------------------------
        if st["disabled"]:
            return GateResult(
                False,
                "DISABLED"
            )

        # ---------------------------------------------------------
        # OFFLINE GRACE
        # ---------------------------------------------------------
        left = grace - (eff - last_ok)

        if left < timedelta(0):
            return GateResult(
                False,
                "NEED_INTERNET"
            )

        return GateResult(
            True,
            "OK",
            left.days
        )

    except Exception:
        return GateResult(
            False,
            "INTERNAL"
        )


# -------------------------------------------------------------
# Compatibility API used by main.py / UI
# -------------------------------------------------------------

def set_active_license(lic):
    _active["license"] = lic


def get_active_license():
    return _active["license"]


def is_feature_enabled(name):
    return _active["license"] is not None


def filter_tabs(tab_names, lic=None):
    return (
        list(tab_names)
        if _active["license"] is not None or lic is not None
        else []
    )


# -------------------------------------------------------------
# Messages
# -------------------------------------------------------------

_MSG = {
    "NEED_INTERNET": (
        "نیاز به اینترنت",
        "برای تأیید لایسنس باید به اینترنت وصل شوید "
        "(حداکثر %d روز بدون اتصال مجاز است)." %
        OFFLINE_GRACE_DAYS
    ),

    "INVALID_CODE": (
        "کد نامعتبر",
        "این کد معتبر نیست. دوباره تلاش کنید."
    ),

    "DISABLED": (
        "لایسنس غیرفعال",
        "این لایسنس غیرفعال شده است."
    ),

    "INTERNAL": (
        "خطا",
        "خطای داخلی در بررسی لایسنس."
    ),
}


def _msg(code):
    t, b = _MSG.get(
        code,
        _MSG["INTERNAL"]
    )

    return (
        messages_fa.rtl(t),
        messages_fa.rtl(b)
    )


# -------------------------------------------------------------
# Startup gate
# -------------------------------------------------------------

def run_startup_gate(app):
    """
    Returns a truthy GateResult when allowed.
    Returns None when the user cancels.
    """

    from tkinter import messagebox, simpledialog

    code = None
    force = False

    while True:

        r = run_checks(
            code=code,
            force=force
        )

        # -----------------------------------------------------
        # LICENSE OK
        # -----------------------------------------------------

        if r.ok:
            return r

        # -----------------------------------------------------
        # NEED CODE / INVALID CODE / DISABLED
        # -----------------------------------------------------

        if r.code in (
            "NEED_CODE",
            "INVALID_CODE",
            "DISABLED"
        ):

            if r.code == "INVALID_CODE":
                messagebox.showerror(
                    *_msg("INVALID_CODE")
                )

            elif r.code == "DISABLED":
                messagebox.showwarning(
                    messages_fa.rtl(
                        "لایسنس غیرفعال"
                    ),
                    messages_fa.rtl(
                        "این لایسنس غیرفعال شده است.\n"
                        "لطفاً کد لایسنس جدید را وارد کنید."
                    ),
                    parent=app
                )

            code = simpledialog.askstring(
                messages_fa.rtl("فعال‌سازی"),
                messages_fa.rtl(
                    "کد لایسنس را وارد کنید:"
                ),
                parent=app
            )

            if not code:
                return None

            # Important:
            # The next run_checks() will verify THIS code
            # instead of the old stored license.
            force = True
            continue

        # -----------------------------------------------------
        # INTERNET REQUIRED
        # -----------------------------------------------------

        if r.code == "NEED_INTERNET":

            title, body = _msg(
                "NEED_INTERNET"
            )

            if messagebox.askretrycancel(
                title,
                body,
                parent=app
            ):
                force = True
                code = None
                continue

            return None

        # -----------------------------------------------------
        # INTERNAL ERROR
        # -----------------------------------------------------

        title, body = _msg(
            r.code
        )

        messagebox.showerror(
            title,
            body,
            parent=app
        )

        return None


# -------------------------------------------------------------
# Background monitor
# -------------------------------------------------------------

class LicenseMonitor:
    """
    First background check ~2 seconds after start,
    then every 5 minutes.
    Network verification happens according to CHECK_INTERVAL.
    """

    def __init__(
        self,
        app,
        local_seconds=300
    ):
        self.app = app
        self.ms = int(
            local_seconds * 1000
        )

        self.results = queue.Queue()
        self.busy = False
        self.first = True

    def start(self):
        self.app.after(
            2000,
            self._tick
        )

        self.app.after(
            1000,
            self._poll
        )

    def _tick(self):

        if not self.busy:

            self.busy = True

            force = self.first
            self.first = False

            threading.Thread(
                target=lambda:
                    self.results.put(
                        run_checks(
                            force=force
                        )
                    ),
                daemon=True
            ).start()

        self.app.after(
            self.ms,
            self._tick
        )

    def _poll(self):

        try:

            while True:

                r = self.results.get_nowait()

                self.busy = False

                if not r.ok:

                    from tkinter import messagebox

                    messagebox.showerror(
                        *_msg(r.code)
                    )

                    try:
                        self.app.destroy()
                    except Exception:
                        pass

                    return

        except queue.Empty:
            pass

        self.app.after(
            1000,
            self._poll
        )

