"""
Liquid Glass 2 - every customtkinter widget gets the frosted-glass look.

Tkinter widgets cannot be truly transparent, so "glass" is built the way
visionOS / Windows 11 dark glass reads visually:

  * fills are LIGHTER than the surface behind them (a see-through pane
    lightens what is below it - it never darkens it)
  * saturated buttons become TINTED glass: a low-strength tint of their
    colour as the fill and the full colour as a thin rim
  * one soft light rim everywhere, nothing heavy or solid

The constructors of the CTk widgets are wrapped once; options a screen
sets itself still win.  Call apply_glass_defaults() before the first
widget is created.
"""

import customtkinter as ctk

from config import (
    GLASS_FIELD, GLASS_EDGE, GLASS_TINT_BASE as PANEL, CARD, CARD_HOVER, TRACK, TEXT, TEXT2,
    BLUE, BLUE_HOVER, GREEN, GREEN_HOVER, DELETE, DELETE_HOVER,
    VIEW, VIEW_HOVER, NEUTRAL, NEUTRAL_HOVER, ORANGE,
)

_applied = False


def _rgb(color):
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def _mix(a, b, t):
    a, b = _rgb(a), _rgb(b)
    return "#%02X%02X%02X" % tuple(
        int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3)
    )


# accent colour  ->  (fill, hover fill, rim)   all derived from the surface
def _tint(color, hover=None):
    return (
        _mix(PANEL, color, 0.30),          # fill  : 30 % colour on the pane
        _mix(PANEL, color, 0.48),          # hover : brighter
        _mix(PANEL, color, 0.85),          # rim   : almost the full colour
    )


GLASS_BUTTONS = {
    BLUE: _tint(BLUE),
    GREEN: _tint(GREEN),
    DELETE: _tint(DELETE),
    VIEW: _tint(VIEW),
    NEUTRAL: _tint(NEUTRAL),
    ORANGE: _tint(ORANGE),
}


def _wrap(cls, defaults, frame_like=False):

    original = cls.__init__

    def __init__(self, *args, **kwargs):

        if not (frame_like and kwargs.get("fg_color") == "transparent"):
            for key, value in defaults.items():
                kwargs.setdefault(key, value)

        original(self, *args, **kwargs)

    cls.__init__ = __init__


def _wrap_button():

    original = ctk.CTkButton.__init__

    def __init__(self, *args, **kwargs):

        fg = kwargs.get("fg_color")

        if fg == "transparent":
            # airy tab / ghost button: no rim, glass hover
            kwargs.setdefault("border_width", 0)
            kwargs.setdefault("hover_color", CARD_HOVER)

        elif fg in GLASS_BUTTONS:
            fill, hover, rim = GLASS_BUTTONS[fg]

            kwargs["fg_color"] = fill
            kwargs["hover_color"] = hover
            kwargs.setdefault("border_width", 1)
            kwargs.setdefault("border_color", rim)

        else:
            kwargs.setdefault("fg_color", CARD)
            kwargs.setdefault("hover_color", CARD_HOVER)
            kwargs.setdefault("border_width", 1)
            kwargs.setdefault("border_color", GLASS_EDGE)

        kwargs.setdefault("corner_radius", 14)
        kwargs.setdefault("text_color", TEXT)

        original(self, *args, **kwargs)

    ctk.CTkButton.__init__ = __init__


def apply_glass_defaults():

    global _applied

    if _applied:
        return

    _applied = True

    _wrap(ctk.CTkFrame, {
        "border_width": 1,
        "border_color": GLASS_EDGE,
        "corner_radius": 16,
    }, frame_like=True)

    _wrap_button()

    _wrap(ctk.CTkEntry, {
        "fg_color": GLASS_FIELD,
        "border_color": GLASS_EDGE,
        "border_width": 1,
        "corner_radius": 12,
        "text_color": TEXT,
        "placeholder_text_color": TEXT2,
    })

    _wrap(ctk.CTkTextbox, {
        "fg_color": GLASS_FIELD,
        "border_color": GLASS_EDGE,
        "border_width": 1,
        "corner_radius": 12,
        "text_color": TEXT,
    })

    _wrap(ctk.CTkComboBox, {
        "fg_color": GLASS_FIELD,
        "border_color": GLASS_EDGE,
        "border_width": 1,
        "corner_radius": 12,
        "button_color": CARD_HOVER,
        "button_hover_color": _mix(PANEL, BLUE, 0.5),
        "dropdown_fg_color": CARD,
        "dropdown_hover_color": CARD_HOVER,
        "dropdown_text_color": TEXT,
        "text_color": TEXT,
    })

    _wrap(ctk.CTkOptionMenu, {
        "fg_color": GLASS_FIELD,
        "button_color": CARD_HOVER,
        "button_hover_color": _mix(PANEL, BLUE, 0.5),
        "dropdown_fg_color": CARD,
        "dropdown_hover_color": CARD_HOVER,
        "dropdown_text_color": TEXT,
        "text_color": TEXT,
        "corner_radius": 12,
    })

    _wrap(ctk.CTkProgressBar, {
        "fg_color": TRACK,
        "border_width": 0,
    })

    _wrap(ctk.CTkSegmentedButton, {
        "fg_color": GLASS_FIELD,
        "unselected_color": GLASS_FIELD,
        "unselected_hover_color": CARD_HOVER,
        "selected_color": _mix(PANEL, BLUE, 0.40),
        "selected_hover_color": _mix(PANEL, BLUE, 0.55),
        "corner_radius": 12,
    })

    _wrap(ctk.CTkCheckBox, {
        "border_color": GLASS_EDGE,
        "hover_color": BLUE_HOVER,
        "corner_radius": 6,
    })

    _wrap(ctk.CTkSwitch, {
        "progress_color": BLUE,
        "button_hover_color": BLUE_HOVER,
    })


# ----------------------------------------------------------------------
# GlassTint - panels pick up the colour of the light moving behind them
# ----------------------------------------------------------------------

class GlassTint:
    """
    A Tk panel cannot be see-through, so instead its fill slowly takes on
    the colour of the nebula that is currently behind it.  Changes are
    small (a few colour levels) and eased, so it reads as light passing
    through frosted glass, never as flicker.

        GlassTint(background, [(header, HEADER, 0.9), (nav, HEADER, 0.9),
                               (container, PANEL, 0.5)])
    """

    MAX_SHIFT = 26
    INTERVAL_MS = 700
    EASE = 0.35

    def __init__(self, background, items):

        self.background = background
        self.running = True
        self.NEBULA_BASE = background.base

        self.items = [
            {
                "widget": widget,
                "base": _rgb(base),
                "strength": strength,
                "current": [float(v) for v in _rgb(base)],
                "last": base.upper(),
            }
            for widget, base, strength in items
        ]

        if self.items:
            self.items[0]["widget"].after(self.INTERVAL_MS, self._step)

    def stop(self):
        self.running = False

    def _step(self):

        if not self.running:
            return

        try:

            for item in self.items:

                mean = self.background.mean_color(item["widget"])

                if mean is None:
                    continue

                color = []

                for channel in range(3):

                    shift = (mean[channel] - self.NEBULA_BASE[channel]) * item["strength"]
                    shift = max(-self.MAX_SHIFT, min(self.MAX_SHIFT, shift))

                    target = item["base"][channel] + shift

                    item["current"][channel] += (
                        target - item["current"][channel]
                    ) * self.EASE

                    color.append(item["current"][channel])

                hex_color = "#%02X%02X%02X" % tuple(
                    int(round(v)) for v in color
                )

                if hex_color != item["last"]:
                    item["last"] = hex_color
                    item["widget"].configure(fg_color=hex_color)

            self.items[0]["widget"].after(self.INTERVAL_MS, self._step)

        except Exception:
            # window closing / widget destroyed
            self.running = False
