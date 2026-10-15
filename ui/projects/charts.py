"""
Chart toolkit for the Project Controlling dashboard.

No extra dependency: shapes are drawn with Pillow at 3x resolution and
down-sampled (=> smooth, anti-aliased, rounded), text is real Tk text on
top (=> crisp, native font), hover / tooltips / animation are plain Tk.

Every chart:  set_data(...)  ->  paint()  [shapes]  +  labels()  [text]
and falls back to an elegant empty state when it has nothing to show.
If a chart ever raises while drawing it shows "Chart unavailable" instead
of breaking the page.
"""

import math
import time
import tkinter as tk
import tkinter.font as tkfont
import traceback
from datetime import date

from PIL import Image, ImageDraw, ImageTk

from config import *
from ui.chart_palette import PALETTE, OTHER, distinct_colors

SS = 3                      # supersampling for the final frame
SS_ANIM = 2                 # cheaper while animating


# ==========================================================
# Central chart theme  (one place to restyle every chart)
# ==========================================================

def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    """Blend colour a -> b by t (0..1), returns '#rrggbb'."""
    ra, rb = _rgb(a), _rgb(b)
    return "#%02x%02x%02x" % tuple(round(ra[i] + (rb[i] - ra[i]) * t) for i in range(3))


CYAN = "#38BDF8"
VIOLET = "#A78BFA"
PINK = "#F472B6"


class ChartTheme:
    bg = CARD
    track = mix(CARD, TEXT, 0.10)
    grid = mix(CARD, TEXT, 0.08)
    hover_bg = mix(CARD, TEXT, 0.06)
    text = TEXT
    muted = TEXT2
    tip_bg = HEADER
    tip_border = BORDER
    progress = CYAN
    # semantic status colours - the same meaning everywhere
    status = {
        "completed": GREEN,
        "in progress": BLUE,
        "pending": "#8B95A7",
        "planned": "#8B95A7",
        "delayed": ORANGE,
        "skipped": mix("#8B95A7", CARD, 0.35),
        "cancelled": RED,
        "canceled": RED,
        "on hold": YELLOW,
        "open": BLUE,
        "closed": "#8B95A7",
    }
    # categorical (expenses only): restrained, ordered, never rainbow
    categories = [BLUE, CYAN, VIOLET, ORANGE, GREEN, PINK]     # legacy (kept for old call sites)
    palette = PALETTE                                          # 14-colour categorical palette
    other = "#8B95A7"


T = ChartTheme


def status_color(name):
    return T.status.get(str(name or "").strip().lower(), T.other)


def category_colors(names, preferred=None):
    """{name: colour} for the categories visible in ONE chart (see ui/chart_palette.py).
    "Other" keeps the neutral grey; names never share a colour while palette colours remain."""
    return distinct_colors(list(names), preferred=preferred, fixed={"Other": OTHER})


def status_colors(names):
    """Semantic status colours, de-duplicated among the statuses visible in one chart
    (e.g. 'Open' and 'In Progress' are both blue by meaning, so the second gets a distinct hue)."""
    names = list(names)
    return distinct_colors(names, preferred={n: status_color(n) for n in names})


def fmt_money(v):
    return f"{v:,.0f} {CURRENCY}"


def fmt_compact(v):
    a = abs(v)
    for limit, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if a >= limit:
            s = f"{v / limit:.1f}".rstrip("0").rstrip(".")
            return s + suffix
    return f"{v:,.0f}"


# ==========================================================
# Base chart
# ==========================================================

class Chart(tk.Canvas):

    anim_ms = 0

    def __init__(self, master, height=240):

        super().__init__(
            master, bg=T.bg, highlightthickness=0, bd=0, height=height
        )

        self._cw = self._ch = 0
        self._t = 1.0
        self._photo = None
        self._hover = None
        self._mouse = (0, 0)
        self._job = None
        self._want_anim = True
        self._ss = SS
        self._fonts = {}
        self._broken = False

        self.bind("<Configure>", self._on_configure)
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", self._on_leave)

    # ---- to override ------------------------------------------------
    def is_empty(self):
        return False

    empty_title = "No data available"
    empty_hint = ""

    def paint(self, d, S, w, h, t):          # shapes (Pillow, coords * S)
        pass

    def labels(self, w, h, t):               # text (Tk canvas)
        pass

    def hit(self, x, y):                     # -> hashable key | None
        return None

    def tip(self, key):                      # -> [(text, color, bold)]
        return []

    # ---- helpers ----------------------------------------------------
    def font(self, size=10, bold=False):
        key = (size, bold)
        if key not in self._fonts:
            self._fonts[key] = tkfont.Font(
                family="Segoe UI", size=size, weight="bold" if bold else "normal"
            )
        return self._fonts[key]

    def text(self, x, y, s, size=10, bold=False, fill=None, anchor="w", **kw):
        return self.create_text(
            x, y, text=s, fill=fill or T.muted, anchor=anchor,
            font=self.font(size, bold), **kw
        )

    def fit(self, s, size, bold, max_w):
        """Ellipsize s so it fits max_w pixels."""
        f = self.font(size, bold)
        if f.measure(s) <= max_w:
            return s
        while len(s) > 1 and f.measure(s + "…") > max_w:
            s = s[:-1]
        return s + "…"

    # ---- rendering --------------------------------------------------
    def _on_configure(self, e):
        if abs(e.width - self._cw) > 1 or abs(e.height - self._ch) > 1:
            self._cw, self._ch = e.width, e.height
            self.render()

    def refresh(self):
        """Call after set_data()."""
        self._want_anim = True
        self._hover = None
        if self._cw > 20:
            self.render()

    def render(self):

        w, h = self._cw, self._ch

        if w < 40 or h < 40:
            return

        self.delete("all")

        try:
            if self.is_empty():
                self._draw_empty(w, h, self.empty_title, self.empty_hint)
                return

            S = self._ss if self._t < 1 else SS
            img = Image.new("RGB", (w * S, h * S), _rgb(T.bg))
            self.paint(ImageDraw.Draw(img), S, w, h, self._t)
            img = img.resize((w, h), Image.LANCZOS)
            self._photo = ImageTk.PhotoImage(img)
            self.create_image(0, 0, image=self._photo, anchor="nw")
            self.labels(w, h, self._t)
            self._draw_tip()

            if self._want_anim and self.anim_ms and not self._broken:
                self._want_anim = False
                self.after(20, self._animate)

        except Exception:                        # never break the page
            traceback.print_exc()
            self._broken = True
            self.delete("all")
            self._draw_empty(w, h, "Chart unavailable", "")

    def _animate(self):

        start = time.time()
        self._ss = SS_ANIM

        def step():
            if not self.winfo_exists():
                return
            p = min(1.0, (time.time() - start) * 1000 / self.anim_ms)
            self._t = 1 - (1 - p) ** 3                   # ease-out
            if p >= 1:
                self._t = 1.0
            self.render()
            if p < 1:
                self._job = self.after(30, step)

        step()

    def _draw_empty(self, w, h, title, hint):
        cx, cy = w / 2, h / 2 - 14
        self.create_oval(cx - 22, cy - 22, cx + 22, cy + 22, outline=T.grid, width=2)
        self.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill=T.grid, outline="")
        self.text(cx, cy + 40, title, 12, True, T.muted, "center")
        if hint:
            self.text(cx, cy + 62, hint, 10, False, mix(T.bg, T.muted, 0.6), "center",
                      width=max(w - 40, 80), justify="center")

    # ---- hover / tooltip -------------------------------------------
    def _on_motion(self, e):
        if self._t < 1 or self.is_empty() or self._broken:
            return
        self._mouse = (e.x, e.y)
        key = self.hit(e.x, e.y)
        if key != self._hover:
            self._hover = key
            self.render()
        else:
            self.delete("tip")
            self._draw_tip()

    def _on_leave(self, _e):
        if self._hover is not None:
            self._hover = None
            self.render()

    def _draw_tip(self):
        self.delete("tip")
        if self._hover is None:
            return
        try:
            lines = self.tip(self._hover)
        except (IndexError, KeyError):  # داده عوض شده یا اندیس لبه‌ای
            self._hover = None
            return
        if not lines:
            return
        # ... بقیه‌ی تابع بدون تغییر

        fn, fb = self.font(10), self.font(10, True)
        width = max((fb if b else fn).measure(t) for t, _c, b in lines) + 24
        height = len(lines) * 20 + 14

        x = self._mouse[0] + 16
        y = self._mouse[1] + 12

        if x + width > self._cw - 4:
            x = self._mouse[0] - width - 12
        if y + height > self._ch - 4:
            y = self._ch - height - 4
        x, y = max(4, x), max(4, y)

        self.create_rectangle(x + 2, y + 3, x + width + 2, y + height + 3,
                              fill=mix(T.bg, "#000000", 0.35), outline="", tags="tip")
        self.create_rectangle(x, y, x + width, y + height,
                              fill=T.tip_bg, outline=T.tip_border, tags="tip")

        for i, (t, c, b) in enumerate(lines):
            self.create_text(x + 12, y + 17 + i * 20, text=t, anchor="w",
                             fill=c or T.text, font=fb if b else fn, tags="tip")


# ==========================================================
# Pillow helpers
# ==========================================================

def rrect(d, box, radius, fill):
    x0, y0, x1, y1 = box
    if x1 - x0 < 1 or y1 - y0 < 1:
        return
    d.rounded_rectangle(box, radius=min(radius, (x1 - x0) / 2, (y1 - y0) / 2), fill=fill)


def ring_arc(d, cx, cy, r, th, a0, a1, color, round_caps=False):
    """Arc of a ring (angles in degrees, 0 = 3 o'clock, clockwise)."""
    d.arc([cx - r, cy - r, cx + r, cy + r], a0, a1, fill=color, width=max(1, int(th)))
    if round_caps:
        rm = r - th / 2
        for a in (a0, a1):
            x = cx + rm * math.cos(math.radians(a))
            y = cy + rm * math.sin(math.radians(a))
            d.ellipse([x - th / 2, y - th / 2, x + th / 2, y + th / 2], fill=color)


# ==========================================================
# 1. Progress ring
# ==========================================================

class ProgressRing(Chart):

    anim_ms = 900

    def __init__(self, master, height=250):
        super().__init__(master, height)
        self.value = None
        self.info = []

    def set_data(self, value, info=None, has_data=True):
        self.value = value if has_data else None
        self.info = info or []
        self.refresh()

    def is_empty(self):
        return self.value is None

    empty_title = "No progress data"
    empty_hint = "Add phases to this project to track progress."

    def _geo(self, w, h):
        r = min(w, h) / 2 - 12
        return w / 2, h / 2, r, max(10, r * 0.15)

    def paint(self, d, S, w, h, t):
        cx, cy, r, th = self._geo(w, h)
        done = self.value >= 99.999
        color = GREEN if done else T.progress
        d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], fill=mix(T.bg, T.track, 0.45))
        d.ellipse([(cx - r + th) * S, (cy - r + th) * S, (cx + r - th) * S, (cy + r - th) * S], fill=T.bg)
        sweep = min(359.9, 360 * self.value / 100 * t)
        if self.value > 0 and sweep > 0.4:
            ring_arc(d, cx * S, cy * S, r * S, th * S, -90, -90 + sweep, color, True)
        elif self.value > 0:
            pass

    def labels(self, w, h, t):
        cx, cy, r, th = self._geo(w, h)
        shown = self.value * t
        self.text(cx, cy - 8, f"{shown:.0f}%", max(18, int(r * 0.34)), True, T.text, "center")
        self.text(cx, cy + r * 0.28, "Overall Progress", 10, False, T.muted, "center")

    def hit(self, x, y):
        cx, cy, r, th = self._geo(self._cw, self._ch)
        return 1 if math.hypot(x - cx, y - cy) <= r else None

    def tip(self, key):
        return [("Weighted progress", T.muted, False),
                (f"{self.value:.1f}%", T.progress, True)] + [(i, None, False) for i in self.info]


# ==========================================================
# 2. Donut (phase status / expense categories)
# ==========================================================

class Donut(Chart):

    anim_ms = 700

    def __init__(self, master, height=250, money=False):
        super().__init__(master, height)
        self.segs = []            # (label, value, color, extra_tip)
        self.center = ("", "")
        self.money = money

    def set_data(self, segs, center_title="", center_sub=""):
        self.segs = [s for s in segs if s[1] > 0]
        self.center = (center_title, center_sub)
        self.refresh()

    def is_empty(self):
        return not self.segs

    def _geo(self, w, h):
        size = min(h - 16, w * 0.46)
        r = size / 2
        cx = 8 + r
        return cx, h / 2, r, max(12, r * 0.24)

    def _total(self):
        return sum(s[1] for s in self.segs)

    def _angles(self, t):
        total, a, out = self._total(), -90.0, []
        gap = 2.6 if len(self.segs) > 1 else 0
        for label, v, col, _ in self.segs:
            span = v / total * 360 * t
            out.append((a + gap / 2, a + span - gap / 2))
            a += span
        return out

    def paint(self, d, S, w, h, t):
        cx, cy, r, th = self._geo(w, h)
        d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], fill=mix(T.bg, T.track, 0.35))
        d.ellipse([(cx - r + th) * S, (cy - r + th) * S, (cx + r - th) * S, (cy + r - th) * S], fill=T.bg)
        for i, ((a0, a1), seg) in enumerate(zip(self._angles(t), self.segs)):
            if a1 - a0 < 0.3:
                continue
            col = seg[2]
            grow = 5 if self._hover == i and t >= 1 else 0
            if self._hover not in (None, i):
                col = mix(col, T.bg, 0.45)
            ring_arc(d, cx * S, cy * S, (r + grow) * S, (th + grow) * S, a0, a1, col)

    def labels(self, w, h, t):
        cx, cy, r, th = self._geo(w, h)
        self.text(cx, cy - 8, self.center[0], max(14, int(r * 0.26)), True, T.text, "center")
        self.text(cx, cy + r * 0.22, self.center[1], 9, False, T.muted, "center")

        total = self._total()
        x0 = cx + r + 30
        row = 26
        y = h / 2 - len(self.segs) * row / 2 + row / 2
        for i, (label, v, col, _) in enumerate(self.segs):
            active = self._hover == i
            self.create_oval(x0, y - 5, x0 + 10, y + 5, fill=col, outline="")
            val = (fmt_compact(v) if self.money else f"{v:g}") + f"  ·  {v / total * 100:.0f}%"
            vw = self.font(10, True).measure(val)
            self.text(x0 + 18, y, self.fit(label, 10, active, max(40, w - x0 - vw - 40)),
                      10, active, T.text if active else T.muted)
            self.text(w - 8, y, val, 10, True, T.text, "e")
            y += row

    def hit(self, x, y):
        cx, cy, r, th = self._geo(self._cw, self._ch)
        dist = math.hypot(x - cx, y - cy)
        if r - th - 4 <= dist <= r + 8:
            ang = (math.degrees(math.atan2(y - cy, x - cx)) + 90) % 360
            total, acc = self._total(), 0
            for i, s in enumerate(self.segs):
                acc += s[1] / total * 360
                if ang <= acc:
                    return i
        x0 = cx + r + 30
        row = 26
        top = h = self._ch / 2 - len(self.segs) * row / 2
        if x >= x0 and top <= y <= top + len(self.segs) * row:
            return min(len(self.segs) - 1, int((y - top) // row))
        return None

    def tip(self, i):
        label, v, col, extra = self.segs[i]
        total = self._total()
        val = fmt_money(v) if self.money else f"{v:g}"
        return ([(label, col, True), (f"{val}  ({v / total * 100:.1f}%)", None, False)]
                + [(e, T.muted, False) for e in (extra or [])])


# ==========================================================
# 3. Phase progress bars (horizontal)
# ==========================================================

class PhaseBars(Chart):

    anim_ms = 800
    ROW = 36

    def __init__(self, master):
        super().__init__(master, 120)
        self.rows = []

    def set_data(self, rows):
        self.rows = rows
        self.configure(height=max(120, len(rows) * self.ROW + 16))
        self.refresh()

    def is_empty(self):
        return not self.rows

    empty_title = "No phase data available"
    empty_hint = "This project has no phases yet."

    def _geo(self, w):
        label_w = min(max(110, max((self.font(10).measure(r["name"]) for r in self.rows), default=110) + 6), w * 0.38)
        return label_w, label_w + 14, w - 60

    def paint(self, d, S, w, h, t):
        _lw, x0, x1 = self._geo(w)
        bh = 12
        for i, r in enumerate(self.rows):
            y = 8 + i * self.ROW
            if self._hover == i:
                rrect(d, (4 * S, y * S, (w - 4) * S, (y + self.ROW - 4) * S), 8 * S, T.hover_bg)
            cy = y + (self.ROW - 4) / 2
            rrect(d, (x0 * S, (cy - bh / 2) * S, x1 * S, (cy + bh / 2) * S), bh / 2 * S, T.track)
            wd = (x1 - x0) * r["progress"] / 100 * t
            if wd >= 1:
                rrect(d, (x0 * S, (cy - bh / 2) * S, (x0 + max(wd, bh * 0.6)) * S, (cy + bh / 2) * S),
                      bh / 2 * S, r["color"])

    def labels(self, w, h, t):
        lw, x0, x1 = self._geo(w)
        for i, r in enumerate(self.rows):
            cy = 8 + i * self.ROW + (self.ROW - 4) / 2
            self.text(10, cy, self.fit(r["name"], 10, self._hover == i, lw),
                      10, self._hover == i, T.text if self._hover == i else T.muted)
            self.text(w - 8, cy, f"{r['progress'] * t:.0f}%", 10, True, T.text, "e")

    def hit(self, x, y):
        i = int((y - 8) // self.ROW)
        return i if 0 <= i < len(self.rows) else None

    def tip(self, i):
        r = self.rows[i]
        return [(r["name"], r["color"], True),
                (f"Progress: {r['progress']:.0f}%", None, False),
                (f"Weight: {r['weight']:g}%", None, False),
                (f"Status: {r['status']}", r["color"], False)]


# ==========================================================
# 4. Timeline / Gantt
# ==========================================================

class Timeline(Chart):

    ROW = 34
    AXIS = 44

    def __init__(self, master):
        super().__init__(master, 160)
        self.rows, self.lo, self.hi = [], None, None

    def set_data(self, rows, lo, hi):
        """rows: dict(name, start, end (date|None), progress, status, color, overdue, label)"""
        self.rows = rows
        dated = [r for r in rows if r["start"] and r["end"]]
        pts = [d for r in dated for d in (r["start"], r["end"])] + [x for x in (lo, hi) if x]
        self.lo, self.hi = (min(pts), max(pts)) if pts else (None, None)
        self.configure(height=self.AXIS + 10 + max(1, len(rows)) * self.ROW + 14)
        self.refresh()

    def is_empty(self):
        return not self.rows or self.lo is None

    empty_title = "No timeline data available"
    empty_hint = "Phases need start and end dates to appear on the timeline."

    def _geo(self, w):
        lw = min(max(120, max((self.font(10).measure(r["name"]) for r in self.rows), default=120) + 6), w * 0.24)
        return lw, lw + 18, w - 24

    def _x(self, day, x0, x1):
        span = max((self.hi - self.lo).days, 1)
        return x0 + (x1 - x0) * (day - self.lo).days / span

    def paint(self, d, S, w, h, t):
        lw, x0, x1 = self._geo(w)
        top = self.AXIS
        for k in range(6):                                       # grid
            gx = x0 + (x1 - x0) * k / 5
            d.line([gx * S, (top - 6) * S, gx * S, (h - 8) * S], fill=T.grid, width=max(1, S))
        bh = 14
        for i, r in enumerate(self.rows):
            y = top + 4 + i * self.ROW
            if self._hover == i:
                rrect(d, (4 * S, y * S, (w - 4) * S, (y + self.ROW - 4) * S), 8 * S, T.hover_bg)
            if not (r["start"] and r["end"]):
                continue
            cy = y + (self.ROW - 4) / 2
            xs, xe = self._x(r["start"], x0, x1), self._x(r["end"], x0, x1)
            xe = max(xe, xs + 8)
            rrect(d, (xs * S, (cy - bh / 2) * S, xe * S, (cy + bh / 2) * S), bh / 2 * S, mix(T.bg, r["color"], 0.28))
            fw = (xe - xs) * r["progress"] / 100 * t
            if fw >= 1:
                rrect(d, (xs * S, (cy - bh / 2) * S, (xs + max(fw, bh * 0.7)) * S, (cy + bh / 2) * S),
                      bh / 2 * S, r["color"])
        today = date.today()
        if self.lo <= today <= self.hi:                          # today marker
            tx = self._x(today, x0, x1)
            yy = top - 8
            while yy < h - 8:
                d.line([tx * S, yy * S, tx * S, min(yy + 5, h - 8) * S], fill=CYAN, width=int(1.6 * S))
                yy += 9

    def labels(self, w, h, t):
        from utils.date_converter import gregorian_to_jalali as j
        lw, x0, x1 = self._geo(w)
        for k in range(6):                                       # axis labels
            day = date.fromordinal(self.lo.toordinal() + round((self.hi - self.lo).days * k / 5))
            gx = x0 + (x1 - x0) * k / 5
            anchor = "w" if k == 0 else ("e" if k == 5 else "center")
            if k in (0, 5):
                self.text(gx, 10, "PROJECT START" if k == 0 else "PROJECT END", 8, True, CYAN, anchor)
            self.text(gx, 27, j(day.isoformat()), 9, False, T.muted, anchor)
        today = date.today()
        if self.lo <= today <= self.hi:
            tx = self._x(today, x0, x1)
            self.create_rectangle(tx - 24, 2, tx + 24, 18, fill=CYAN, outline="")
            self.text(tx, 10, "TODAY", 8, True, T.bg, "center")
        for i, r in enumerate(self.rows):
            cy = self.AXIS + 4 + i * self.ROW + (self.ROW - 4) / 2
            hv = self._hover == i
            self.text(10, cy, self.fit(r["name"], 10, hv, lw), 10, hv, T.text if hv else T.muted)
            if not (r["start"] and r["end"]):
                self.text(x0, cy, "no dates set", 9, False, mix(T.bg, T.muted, 0.6))

    def hit(self, x, y):
        i = int((y - self.AXIS - 4) // self.ROW)
        return i if 0 <= i < len(self.rows) and y > self.AXIS else None

    def tip(self, i):
        from utils.date_converter import gregorian_to_jalali as j
        r = self.rows[i]
        lines = [(r["name"], r["color"], True)]
        if r["start"] and r["end"]:
            lines.append((f"{j(r['start'].isoformat())}  →  {j(r['end'].isoformat())}", None, False))
        lines += [(f"Progress: {r['progress']:.0f}%", None, False),
                  (f"Status: {r['label']}", r["color"], False)]
        return lines


# ==========================================================
# 5. Smooth line chart (expense trend)
# ==========================================================

class LineChart(Chart):

    anim_ms = 0
    PL, PR, PT, PB = 58, 34, 18, 34

    def __init__(self, master, height=250):
        super().__init__(master, height)
        self.pts = []                   # (label, value)

    def set_data(self, pts):
        self.pts = pts
        self.refresh()

    def is_empty(self):
        return len(self.pts) < 2

    empty_title = "Not enough data for a trend"
    empty_hint = "Expenses from at least two different months are needed."

    def _scale(self, w, h):
        top = max(v for _, v in self.pts) or 1
        step = 10 ** math.floor(math.log10(top))
        ymax = math.ceil(top * 1.12 / step * 2) / 2 * step
        return ymax, self.PL, w - self.PR, self.PT, h - self.PB

    def _xy(self, i, v, w, h):
        ymax, x0, x1, y0, y1 = self._scale(w, h)
        n = len(self.pts)
        return x0 + (x1 - x0) * i / (n - 1), y1 - (y1 - y0) * v / ymax

    def _curve(self, w, h, S):
        P = [self._xy(i, v, w, h) for i, (_l, v) in enumerate(self.pts)]
        base = h - self.PB
        out = []
        for i in range(len(P) - 1):
            p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, len(P) - 1)]
            for k in range(14):
                u = k / 14
                x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * u + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * u * u
                           + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * u ** 3)
                y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * u + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * u * u
                           + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * u ** 3)
                out.append((x * S, min(y, base) * S))
        out.append((P[-1][0] * S, P[-1][1] * S))
        return out

    def paint(self, d, S, w, h, t):
        ymax, x0, x1, y0, y1 = self._scale(w, h)
        for k in range(5):
            gy = y1 - (y1 - y0) * k / 4
            d.line([x0 * S, gy * S, x1 * S, gy * S], fill=T.grid, width=max(1, S))
        curve = self._curve(w, h, S)
        d.polygon(curve + [(x1 * S, y1 * S), (x0 * S, y1 * S)], fill=mix(T.bg, T.progress, 0.10))
        d.line(curve, fill=T.progress, width=int(3 * S), joint="curve")
        for i, (_l, v) in enumerate(self.pts):
            px, py = self._xy(i, v, w, h)
            act = self._hover == i
            if act:
                d.line([px * S, y0 * S, px * S, y1 * S], fill=mix(T.bg, T.progress, 0.35), width=S)
            rr = (6 if act else 4) * S
            d.ellipse([px * S - rr, py * S - rr, px * S + rr, py * S + rr], fill=T.bg, outline=T.progress, width=int(2 * S))

    def labels(self, w, h, t):
        ymax, x0, x1, y0, y1 = self._scale(w, h)
        for k in range(5):
            gy = y1 - (y1 - y0) * k / 4
            self.text(x0 - 10, gy, fmt_compact(ymax * k / 4), 9, False, T.muted, "e")
        n = len(self.pts)
        every = max(1, math.ceil(n / max(2, (x1 - x0) // 70)))
        for i, (lab, _v) in enumerate(self.pts):
            if i % every == 0 or i == n - 1:
                px, _ = self._xy(i, 0, w, h)
                self.text(px, y1 + 18, lab, 9, self._hover == i, T.text if self._hover == i else T.muted, "center")

    def hit(self, x, y):
        n = len(self.pts)
        _ymax, x0, x1, y0, y1 = self._scale(self._cw, self._ch)
        if not (x0 - 10 <= x <= x1 + 10 and y0 - 10 <= y <= y1 + 10):
            return None
        return min(n - 1, max(0, round((x - x0) / (x1 - x0) * (n - 1))))

    def tip(self, i):
        lab, v = self.pts[i]
        return [(lab, T.progress, True), (fmt_money(v), None, False)]

# ==========================================================
# 6. Horizontal bars with a value column  (rankings / paid-vs-total)
# ==========================================================

class HBars(Chart):
    """
    rows: [{"label", "value", "total", "color", "display", "tip": [str]}]

    * value / total share one scale (the biggest total fills the track), so
      bars are comparable between rows.
    * total == value  -> plain ranking bar (e.g. expenses by category)
    * total  > value  -> faint track = total, solid part = value
      (e.g. paid out of contract value)
    """

    anim_ms = 800
    ROW = 36

    empty_title = "No data available"
    empty_hint = ""

    def __init__(self, master, height=120):
        super().__init__(master, height)
        self.rows = []

    def set_data(self, rows):
        self.rows = list(rows)
        self.configure(height=max(120, len(self.rows) * self.ROW + 16))
        self.refresh()

    def is_empty(self):
        return not self.rows

    def _geo(self, w):
        f = self.font(10)
        label_w = min(max(90, max((f.measure(r["label"]) for r in self.rows), default=90) + 6), w * 0.32)
        value_w = min(max(60, max((self.font(10, True).measure(r["display"]) for r in self.rows), default=60) + 8), w * 0.30)
        return label_w, label_w + 14, w - value_w - 14

    def paint(self, d, S, w, h, t):
        _lw, x0, x1 = self._geo(w)
        top = max((r["total"] for r in self.rows), default=0) or 1
        bh = 12
        for i, r in enumerate(self.rows):
            y = 8 + i * self.ROW
            if self._hover == i:
                rrect(d, (4 * S, y * S, (w - 4) * S, (y + self.ROW - 4) * S), 8 * S, T.hover_bg)
            cy = y + (self.ROW - 4) / 2
            span = x1 - x0
            track_x = x0 + max(span * r["total"] / top, bh)
            rrect(d, (x0 * S, (cy - bh / 2) * S, track_x * S, (cy + bh / 2) * S), bh / 2 * S, T.track)
            if r["value"] > 0:
                fx = x0 + max(span * r["value"] / top * t, bh * 0.6)
                rrect(d, (x0 * S, (cy - bh / 2) * S, fx * S, (cy + bh / 2) * S), bh / 2 * S, r["color"])

    def labels(self, w, h, t):
        lw, _x0, _x1 = self._geo(w)
        for i, r in enumerate(self.rows):
            cy = 8 + i * self.ROW + (self.ROW - 4) / 2
            active = self._hover == i
            self.text(10, cy, self.fit(r["label"], 10, active, lw), 10, active,
                      T.text if active else T.muted)
            self.text(w - 8, cy, r["display"], 10, True, T.text, "e")

    def hit(self, x, y):
        i = int((y - 8) // self.ROW)
        return i if 0 <= i < len(self.rows) else None

    def tip(self, i):
        r = self.rows[i]
        return [(r["label"], r["color"], True)] + [(s, None, False) for s in r.get("tip") or [r["display"]]]
