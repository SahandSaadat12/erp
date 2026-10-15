"""
EXPERIMENTAL - real Windows 11 acrylic behind the window.

Turn on with  settings.json:  { "theme": "Liquid Glass Light", "native_glass": true }

Panels whose colour is KEY become truly see-through (you see the blurred
desktop through them, including behind their text).  Needs Windows 11
22H2+ (build 22621).  On anything else it silently does nothing.
"""

import ctypes
import sys

KEY = "#010203"


def is_supported():

    if not sys.platform.startswith("win"):
        return False

    try:
        return sys.getwindowsversion().build >= 22621
    except Exception:
        return False


class _Margins(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_int), ("right", ctypes.c_int),
        ("top", ctypes.c_int), ("bottom", ctypes.c_int),
    ]


def apply_backdrop(window, dark=True, kind="acrylic"):
    """kind: acrylic (strong blur) | mica (subtle) | tabbed"""

    try:

        window.update_idletasks()

        hwnd = ctypes.windll.user32.GetParent(window.winfo_id()) or window.winfo_id()
        dwm = ctypes.windll.dwmapi

        def set_attr(attribute, value):
            number = ctypes.c_int(value)
            return dwm.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd), attribute,
                ctypes.byref(number), ctypes.sizeof(number)
            )

        set_attr(20, 1 if dark else 0)                                  # dark title bar
        ok = set_attr(38, {"mica": 2, "acrylic": 3, "tabbed": 4}[kind]) == 0

        margins = _Margins(-1, -1, -1, -1)
        dwm.DwmExtendFrameIntoClientArea(ctypes.c_void_p(hwnd), ctypes.byref(margins))

        window.attributes("-transparentcolor", KEY)

        return ok

    except Exception:
        return False
