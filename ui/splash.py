"""
Splash / loading screen.

Unlike the old one (fixed 3.6 s of fake progress) this one is driven by
the REAL start-up stages:

    splash = Splash(app)
    splash.update_status("Opening database", 25)      # called from main.py
    ...
    splash.finish(on_done)                            # fades out when 100 %

The progress bar eases towards the target value, so it never jumps, and
the splash stays at least MIN_SECONDS so it never just flashes.
"""

import math
import random
import time
import tkinter as tk

import customtkinter as ctk

from config import (
    SPLASH_BG,
    SPLASH_GLOW,
    SPLASH_ACCENT,
    SPLASH_TEXT,
    TEXT,
    APP_TITLE,
)

MIN_SECONDS = 1.8
AUTHOR = "Sahand Saadat"


def _rgb(color):
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def _mix(a, b, t):
    a, b = _rgb(a), _rgb(b)
    return "#%02X%02X%02X" % tuple(
        int(a[i] + (b[i] - a[i]) * t) for i in range(3)
    )


class Splash:

    def __init__(self, app):

        self.app = app
        self.started = time.perf_counter()

        self.target = 0.0
        self.progress = 0.0
        self.status = "Starting"
        self._dots = 0
        self._closing = False
        self._running = True

        # ui/splash.py
        def _px(size):  # point -> pixel (منفی = پیکسل در tk)
            return -int(size * 96 / 72)

        # در __init__:
        self.window = tk.Toplevel(app)  # به جای ctk.CTkToplevel
        self.window.overrideredirect(True)
        self.window.configure(bg=SPLASH_BG)  # به جای fg_color
        self.window.attributes("-alpha", 0.0)
        self.window.attributes("-topmost", True)

        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()

        width = int(min(1100, screen_w - 80))
        height = int(min(width * 9 / 16, screen_h - 100))
        width = int(min(width, height * 16 / 9))

        x = (screen_w - width) // 2
        y = (screen_h - height) // 2

        self.w, self.h = width, height

        self.window.geometry(f"{width}x{height}+{x}+{y}")

        self.canvas = tk.Canvas(
            self.window,
            width=width,
            height=height,
            bg=SPLASH_BG,
            highlightthickness=0,
            bd=0
        )

        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)

        self._build()

        self._fade_in()
        self._animate()

    # ------------------------------------------------------------------
    # drawing
    # ------------------------------------------------------------------

    def _build(self):

        cx, cy = self.w / 2, self.h / 2 - 20

        # soft glow (concentric ovals, 5 colours from the theme blended up)
        self.glows = []

        base = SPLASH_GLOW
        steps = []

        for i in range(len(base) - 1):
            for k in range(4):
                steps.append(_mix(base[i], base[i + 1], k / 4))

        steps.append(base[-1])

        for i, color in enumerate(steps):

            size = (1 - i / len(steps)) * min(self.w, self.h) * 0.62

            item = self.canvas.create_oval(
                cx - size * 1.5, cy - size,
                cx + size * 1.5, cy + size,
                fill=color, outline=""
            )

            self.glows.append((item, size))

        # stars
        self.stars = []

        for _ in range(70):

            sx = random.uniform(10, self.w - 10)
            sy = random.uniform(10, self.h - 10)
            size = random.choice([1, 1, 1, 2])

            item = self.canvas.create_oval(
                sx, sy, sx + size, sy + size,
                fill=_mix(SPLASH_BG, SPLASH_TEXT, 0.35), outline=""
            )

            self.stars.append({
                "id": item,
                "speed": random.uniform(0.4, 1.6),
                "phase": random.uniform(0, math.pi * 2),
            })

        # rotating ring around the title
        self.ring_r = min(self.w, self.h) * 0.19

        self.ring_back = self.canvas.create_oval(
            cx - self.ring_r, cy - self.ring_r,
            cx + self.ring_r, cy + self.ring_r,
            outline=_mix(SPLASH_BG, SPLASH_ACCENT, 0.22), width=2
        )

        self.ring_arc = self.canvas.create_arc(
            cx - self.ring_r, cy - self.ring_r,
            cx + self.ring_r, cy + self.ring_r,
            start=90, extent=95,
            style="arc", outline=SPLASH_ACCENT, width=3
        )

        self.ring_arc2 = self.canvas.create_arc(
            cx - self.ring_r - 12, cy - self.ring_r - 12,
            cx + self.ring_r + 12, cy + self.ring_r + 12,
            start=270, extent=40,
            style="arc",
            outline=_mix(SPLASH_BG, SPLASH_ACCENT, 0.55), width=1
        )

        title_size = max(34, int(self.w * 0.052))

        self.canvas.create_text(
            cx, cy - 4,
            text="ERP",
            fill=TEXT,
            font=("Segoe UI", title_size, "bold")
        )

        self.canvas.create_text(
            cx, cy + self.ring_r + 34,
            text=APP_TITLE.upper().replace("ERP ", ""),
            fill=SPLASH_TEXT,
            font=("Segoe UI", max(11, int(self.w * 0.0125)), "bold")
        )

        # status + progress
        self.status_text = self.canvas.create_text(
            self.w / 2, self.h - 98,
            text=self.status.upper(),
            fill=_mix(SPLASH_BG, SPLASH_TEXT, 0.8),
            font=("Segoe UI", max(9, int(self.w * 0.0085)), "bold")
        )

        self.track_w = self.w * 0.30
        self.track_y = self.h - 70

        x0 = self.w / 2 - self.track_w / 2

        self.canvas.create_line(
            x0, self.track_y, x0 + self.track_w, self.track_y,
            fill=_mix(SPLASH_BG, SPLASH_ACCENT, 0.18),
            width=4, capstyle="round"
        )

        self.bar = self.canvas.create_line(
            x0, self.track_y, x0, self.track_y,
            fill=SPLASH_ACCENT, width=4, capstyle="round"
        )

        self.percent_text = self.canvas.create_text(
            self.w / 2 + self.track_w / 2 + 34, self.track_y,
            text="0%",
            fill=_mix(SPLASH_BG, SPLASH_TEXT, 0.7),
            font=("Segoe UI", max(9, int(self.w * 0.008)))
        )

        self.canvas.create_text(
            self.w / 2, self.h - 24,
            text=AUTHOR,
            fill=_mix(SPLASH_BG, SPLASH_TEXT, 0.4),
            font=("Segoe UI", max(8, int(self.w * 0.0075)))
        )

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def update_status(self, text, target):
        self.status = text
        self.target = max(self.target, min(100.0, float(target)))

    def is_ready(self):
        return (
            self.progress >= 99.5
            and time.perf_counter() - self.started >= MIN_SECONDS
        )

    def finish(self, on_done=None):
        """Fade out and destroy. Call once the main window is visible."""

        if self._closing:
            return

        self._closing = True
        self._fade_out(1.0, on_done)

    # ------------------------------------------------------------------
    # animation
    # ------------------------------------------------------------------

    def _alive(self):
        try:
            return self._running and self.window.winfo_exists()
        except tk.TclError:
            return False

    def _fade_in(self, step=0):

        if not self._alive():
            return

        t = min(1.0, step / 14)

        self.window.attributes("-alpha", 1 - (1 - t) ** 3)

        if t < 1:
            self.window.after(16, self._fade_in, step + 1)

    def _fade_out(self, alpha, on_done):

        if not self._alive():
            if on_done:
                on_done()
            return

        alpha -= 0.07

        if alpha <= 0:

            self._running = False

            try:
                self.window.destroy()
            except tk.TclError:
                pass

            if on_done:
                on_done()

            return

        # smooth ease-out
        self.window.attributes("-alpha", alpha * alpha)
        self.window.after(16, self._fade_out, alpha, on_done)

    def _animate(self, t=0):

        if not self._alive():
            return

        # ease progress towards the target
        self.progress += (self.target - self.progress) * 0.09

        if self.target - self.progress < 0.15:
            self.progress = self.target

        x0 = self.w / 2 - self.track_w / 2

        self.canvas.coords(
            self.bar,
            x0, self.track_y,
            x0 + self.track_w * self.progress / 100, self.track_y
        )

        self.canvas.itemconfigure(
            self.percent_text, text=f"{int(self.progress)}%"
        )

        # ring
        self.canvas.itemconfigure(
            self.ring_arc, start=(90 - t * 5.2) % 360
        )

        self.canvas.itemconfigure(
            self.ring_arc2, start=(270 + t * 3.1) % 360
        )

        # stars twinkle (a few per frame)
        for index in range(t % 3, len(self.stars), 3):

            star = self.stars[index]

            level = (math.sin(t * 0.05 * star["speed"] + star["phase"]) + 1) / 2

            self.canvas.itemconfigure(
                star["id"],
                fill=_mix(SPLASH_BG, SPLASH_TEXT, 0.15 + level * 0.65)
            )

        # glow breathing
        cx, cy = self.w / 2, self.h / 2 - 20
        pulse = 1 + math.sin(t * 0.03) * 0.025

        for item, size in self.glows:

            s = size * pulse

            self.canvas.coords(
                item,
                cx - s * 1.5, cy - s,
                cx + s * 1.5, cy + s
            )

        # status text (dots every ~0.5 s)
        if t % 12 == 0:
            self._dots = (self._dots + 1) % 4

            self.canvas.itemconfigure(
                self.status_text,
                text=self.status.upper() + "." * self._dots
            )

        self.window.after(16, self._animate, t + 1)

    def lift(self):
        try:
            self.window.attributes("-topmost", True)
            self.window.lift()
        except tk.TclError:
            pass
