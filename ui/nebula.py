"""
Nebula background - slow flowing ribbons of light over deep space.

No bubbles, no sprites: the whole picture is a procedural light field
(a few soft spectral ribbons + cloud mottling + vignette) rendered with
numpy at LOW resolution, smoothly up-scaled, dithered (no banding) and
shown on one canvas image.  ~15 fps, time based, pauses when the window
is minimised.

Needs numpy + Pillow.  If numpy is missing, main.py falls back to the
old LiveBackground("glass").
"""

import math
import random
import time
import tkinter as tk

import numpy as np
from PIL import Image, ImageChops, ImageTk

FPS = 15
SPEED = 0.22            # global motion speed (lower = calmer)
GRID_W = 300            # simulation width; height follows the window ratio

BASE = np.array([6, 9, 22], dtype=np.float32)          # deep space (dark)

# light "aurora" : pastel ribbons that TINT a bright base instead of glowing
LIGHT_BASE = np.array([236, 241, 251], dtype=np.float32)

RIBBON_COLORS_LIGHT = [
    (116, 160, 255),
    (104, 214, 226),
    (184, 150, 255),
    (255, 160, 210),
    (140, 188, 255),
]

PALETTE_BASE = {
    "dark": (6, 9, 22),
    "light": (236, 241, 251),
}

# (centre_v, thickness, strength, colour, freq1, freq2, speed1, speed2, phase)
RIBBONS = [
    (0.24, 0.052, 0.95, (46, 92, 214),   0.42, 1.10,  0.55, 0.38, 0.4),
    (0.46, 0.060, 0.80, (28, 168, 176),  0.33, 0.85, -0.42, 0.50, 2.1),
    (0.68, 0.055, 0.85, (112, 70, 214),  0.47, 1.20,  0.36, -0.46, 4.0),
    (0.38, 0.110, 0.40, (176, 76, 170),  0.25, 0.70,  0.28, 0.33, 5.2),
    (0.84, 0.048, 0.55, (40, 110, 200),  0.36, 0.95, -0.30, 0.40, 1.1),
]


def render_field(gw, gh, t, palette="dark"):
    """Return uint8 RGB array (gh, gw, 3) of the nebula at time t."""

    aspect = gw / float(gh)

    u = (np.linspace(0.0, 1.0, gw, dtype=np.float32) * aspect)[None, :]
    v = np.linspace(0.0, 1.0, gh, dtype=np.float32)[:, None]

    tau = 2.0 * math.pi
    t = t * SPEED

    light = palette == "light"

    total = np.zeros((gh, gw, 3), dtype=np.float32)
    weight_sum = np.zeros((gh, gw), dtype=np.float32)

    for index, (c, thick, strength, color, f1, f2, s1, s2, ph) in enumerate(RIBBONS):

        if light:
            color = RIBBON_COLORS_LIGHT[index % len(RIBBON_COLORS_LIGHT)]

        centre = (
            c
            + 0.085 * np.sin(u * f1 * tau + t * s1 + ph)
            + 0.045 * np.sin(u * f2 * tau - t * s2 + ph * 1.7)
            + 0.025 * np.sin(u * 3.1 * tau + t * 0.21 + ph * 0.6)
        )

        d = (v - centre) / thick

        core = np.exp(-(d * d))
        halo = np.exp(-(d * d) / 9.0) * 0.34

        # brightness drifts along the ribbon
        along = 0.55 + 0.45 * np.sin(u * 1.7 * tau + t * 0.33 + ph * 2.3)

        weight = (core * 0.85 + halo) * along * strength

        total += weight[:, :, None] * np.array(color, dtype=np.float32)
        weight_sum += weight

    # cloud mottling: slow, low-frequency, makes it feel like gas
    cloud = (
        0.5 + 0.5 * np.sin(
            u * 2.3 * tau * 0.5 + 1.4 * np.sin(v * 3.1 + t * 0.17) + t * 0.11
        )
    ) * (
        0.5 + 0.5 * np.sin(v * 2.7 * tau * 0.5 - u * 1.9 + t * 0.13 + 1.2)
    )

    cloud_gain = (0.72 + 0.55 * cloud)

    if light:

        # average ribbon colour, blended over the bright base by how much
        # light is there  (never gets darker than the pastel colours)
        weight_sum = weight_sum * cloud_gain
        average = total * cloud_gain[:, :, None] / np.maximum(weight_sum, 1e-4)[:, :, None]

        blend = (1.0 - np.exp(-weight_sum / 0.55)) * 0.78

        image = LIGHT_BASE[None, None, :] + (average - LIGHT_BASE[None, None, :]) * blend[:, :, None]

        # very soft edge falloff towards white
        cx = (u / aspect) - 0.5
        cy = v - 0.5
        edge = np.clip((cx * cx + cy * cy) * 1.4, 0, 1) * 0.35

        image = image + (255.0 - image) * edge[:, :, None]

    else:

        total *= cloud_gain[:, :, None]

        total = 1.0 - np.exp(-total / 170.0)
        total *= 200.0

        image = BASE[None, None, :] + total

        cx = (u / aspect) - 0.5
        cy = v - 0.5
        vignette = 1.0 - 0.55 * np.clip((cx * cx * 1.1 + cy * cy * 1.5) * 1.6, 0, 1)

        image *= vignette[:, :, None]

    return np.clip(image, 0, 255).astype(np.uint8)


class NebulaBackground:

    def __init__(self, parent, style="nebula"):

        self.parent = parent

        self.palette = "light" if style == "nebula_light" else "dark"
        self.base = PALETTE_BASE[self.palette]

        self.canvas = tk.Canvas(
            parent,
            bg="#%02X%02X%02X" % self.base,
            highlightthickness=0,
            bd=0
        )

        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)

        self.width = 1500
        self.height = 850

        self._size = None
        self._photo = None
        self._noise = None
        self._field = None
        self._image_item = self.canvas.create_image(
            0, 0, anchor="nw"
        )

        self._running = True
        self._after_id = None
        self._hold_until = 0.0
        self._clock = random.uniform(0, 100)
        self._last = time.perf_counter()

        self._stars = []

        if self.palette == "dark":
            self._build_stars()

        self.canvas.bind("<Configure>", self._on_resize)

        self._tick()

    # ------------------------------------------------------------------

    def _build_stars(self):

        # very sparse, dim "dust" - static, only a hint of depth
        for _ in range(90):

            shade = random.choice([0x2A, 0x36, 0x44, 0x58])
            color = "#%02X%02X%02X" % (shade, shade + 6, shade + 22)

            item = self.canvas.create_oval(0, 0, 0, 0, fill=color, outline="")

            self._stars.append(
                (item, random.random(), random.random(), random.choice([0.6, 0.8, 1.0, 1.3]))
            )

    def _layout_stars(self):

        w, h = self.width, self.height

        for item, nx, ny, r in self._stars:
            x, y = nx * w, ny * h
            self.canvas.coords(item, x - r, y - r, x + r, y + r)

    def _on_resize(self, event):

        if event.width > 1 and event.height > 1:
            self.width = event.width
            self.height = event.height

    # ------------------------------------------------------------------

    def _prepare_size(self):

        w, h = int(self.width), int(self.height)

        if self._size == (w, h):
            return

        self._size = (w, h)

        self._photo = ImageTk.PhotoImage(Image.new("RGB", (w, h)))

        # tiny static noise: removes banding in the dark gradients
        rng = np.random.default_rng(7)
        noise = rng.integers(0, 3, size=(h, w, 3), dtype=np.uint8)
        self._noise = Image.fromarray(noise, "RGB")

        self.canvas.itemconfigure(self._image_item, image=self._photo)
        self.canvas.tag_lower(self._image_item)

        self._layout_stars()

    def _tick(self):

        if not self._running:
            return

        try:

            if not self.canvas.winfo_viewable():
                self._last = time.perf_counter()
                self._after_id = self.canvas.after(400, self._tick)
                return

            now = time.perf_counter()

            if now < self._hold_until:
                self._last = now
                self._after_id = self.canvas.after(40, self._tick)
                return

            self._clock += min(now - self._last, 0.25)
            self._last = now

            self._prepare_size()

            w, h = self._size

            gw = GRID_W
            gh = max(40, int(round(gw * h / float(w))))

            self._field = render_field(gw, gh, self._clock, self.palette)

            small = Image.fromarray(self._field, "RGB")

            frame = small.resize((w, h), Image.BICUBIC)
            frame = ImageChops.add(frame, self._noise)

            self._photo.paste(frame)

            self._after_id = self.canvas.after(int(1000 / FPS), self._tick)

        except tk.TclError:
            self._running = False

    # ------------------------------------------------------------------

    def hold(self, seconds=0.4):
        """Pause drawing briefly (used while a tab is being built)."""
        self._hold_until = time.perf_counter() + seconds

    def mean_color(self, widget):
        """Average nebula colour (r, g, b) currently behind a widget."""

        field = self._field

        if field is None or not self._size:
            return None

        try:
            w, h = self._size
            gh, gw = field.shape[:2]

            x0 = (widget.winfo_rootx() - self.canvas.winfo_rootx()) / float(w)
            y0 = (widget.winfo_rooty() - self.canvas.winfo_rooty()) / float(h)
            x1 = x0 + widget.winfo_width() / float(w)
            y1 = y0 + widget.winfo_height() / float(h)

            ix0 = int(max(0.0, min(1.0, x0)) * (gw - 1))
            ix1 = int(max(0.0, min(1.0, x1)) * (gw - 1)) + 1
            iy0 = int(max(0.0, min(1.0, y0)) * (gh - 1))
            iy1 = int(max(0.0, min(1.0, y1)) * (gh - 1)) + 1

            region = field[iy0:max(iy1, iy0 + 1), ix0:max(ix1, ix0 + 1)]

            return tuple(region.reshape(-1, 3).mean(axis=0))

        except tk.TclError:
            return None

    def stop(self):

        self._running = False

        try:
            if self._after_id:
                self.canvas.after_cancel(self._after_id)
        except tk.TclError:
            pass

        try:
            self.canvas.destroy()
        except tk.TclError:
            pass
