"""
Live (animated) window backgrounds.

    LiveBackground(app, "space")   starfield + drifting nebula + shooting stars
    LiveBackground(app, "glass")   Liquid-Glass aurora + floating glass bubbles

How it works (and why it is cheap):
  * the soft glows are RGBA sprites (real per-pixel alpha, so they blend
    smoothly - no banding like stacked ovals) that are only MOVED every
    frame; nothing is re-rendered.
  * stars / bubbles are plain canvas items; only a fraction of them is
    touched per frame.
  * the animation pauses while the window is minimised / hidden, and runs
    on a time base (not frame count) so speed does not depend on the FPS.
  * everything is laid out in normalised coordinates, so it follows
    window resizing / maximising.

Tkinter cannot make real widgets transparent, so the background is
visible in the gaps around the floating panels (see main.py).
"""

import math
import random
import time
import tkinter as tk

try:
    from PIL import Image, ImageDraw, ImageTk
    _HAS_PIL = True
except Exception:                                    # pragma: no cover
    _HAS_PIL = False


FPS = 24


# ======================================================================
# colour helpers
# ======================================================================

def _rgb(color):
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def _hex(rgb):
    return "#%02X%02X%02X" % tuple(
        max(0, min(255, int(round(v)))) for v in rgb
    )


def _mix(a, b, t):
    a, b = _rgb(a), _rgb(b)
    return _hex(tuple(a[i] + (b[i] - a[i]) * t for i in range(3)))


def _glow_sprite(size, color, peak, falloff):
    """Soft round glow with real alpha."""

    # Image.radial_gradient: 0 in the centre, ~181 at the middle of each
    # edge, 255 in the corners.  Normalise so the glow reaches exactly 0
    # at the edge of the sprite (otherwise the square shows as a hard cut).
    gradient = Image.radial_gradient("L")

    lut = [
        int(((1.0 - min(1.0, v / 181.0)) ** falloff) * 255 * peak)
        for v in range(256)
    ]

    alpha = gradient.point(lut).resize(
        (size, size), Image.BICUBIC
    )

    image = Image.new("RGBA", (size, size), _rgb(color) + (0,))
    image.putalpha(alpha)

    return ImageTk.PhotoImage(image)


def _orb_sprite(size, color):
    """Glass orb: translucent body, bright rim, specular arc (real alpha)."""

    big = size * 3
    image = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    r, g, b = _rgb(color)

    draw.ellipse(
        (3, 3, big - 3, big - 3),
        fill=(r, g, b, 30),
        outline=(255, 255, 255, 120),
        width=max(3, big // 55)
    )

    pad = big * 0.13

    draw.arc(
        (pad, pad, big - pad, big - pad),
        start=195, end=255,
        fill=(255, 255, 255, 190),
        width=max(3, big // 40)
    )

    draw.arc(
        (pad, pad, big - pad, big - pad),
        start=15, end=55,
        fill=(r, g, b, 150),
        width=max(2, big // 70)
    )

    dot = big * 0.2

    draw.ellipse(
        (big * 0.27, big * 0.2, big * 0.27 + dot, big * 0.2 + dot * 0.55),
        fill=(255, 255, 255, 120)
    )

    return ImageTk.PhotoImage(
        image.resize((size, size), Image.LANCZOS)
    )


# ======================================================================
# presets
# ======================================================================

PRESETS = {

    "space": {

        "base": "#050609",

        # (cx, cy, ax, ay, period_x, period_y, size, colour, peak)
        "glows": [
            (0.14, 0.22, 0.05, 0.04, 70, 55, 640, "#1E4C8A", 0.34),
            (0.76, 0.18, 0.06, 0.05, 85, 62, 700, "#2B2F8F", 0.30),
            (0.90, 0.72, 0.05, 0.05, 66, 80, 600, "#144E66", 0.30),
            (0.28, 0.85, 0.06, 0.04, 92, 58, 680, "#3A2A7A", 0.26),
            (0.52, 0.48, 0.08, 0.06, 110, 75, 560, "#17406E", 0.20),
        ],

        "stars": 260,
        "shooting": True,
        "bubbles": 0,
    },

    "glass": {

        "base": "#0A0E1F",

        "glows": [
            (0.12, 0.20, 0.10, 0.08, 38, 46, 820, "#6A4CFF", 0.62),
            (0.82, 0.16, 0.09, 0.10, 44, 36, 780, "#18C8E8", 0.50),
            (0.88, 0.78, 0.10, 0.08, 40, 52, 800, "#E050C8", 0.46),
            (0.22, 0.88, 0.09, 0.09, 50, 42, 760, "#2F6BFF", 0.55),
            (0.52, 0.50, 0.12, 0.10, 58, 48, 640, "#7B5CFF", 0.30),
        ],

        "stars": 0,
        "shooting": False,
        "bubbles": 16,
    },

    "glass2": {

        "base": "#080C1C",

        "glows": [
            (0.10, 0.16, 0.12, 0.09, 34, 44, 900, "#6A4CFF", 0.78),
            (0.84, 0.14, 0.10, 0.12, 40, 32, 860, "#14D2F0", 0.62),
            (0.90, 0.80, 0.11, 0.09, 36, 48, 880, "#FF4FC0", 0.58),
            (0.18, 0.90, 0.10, 0.10, 46, 38, 840, "#2F6BFF", 0.68),
            (0.50, 0.46, 0.14, 0.11, 52, 44, 720, "#8B5CFF", 0.42),
            (0.66, 0.60, 0.10, 0.10, 42, 50, 600, "#25E0B8", 0.30),
        ],

        "stars": 0,
        "shooting": False,
        "bubbles": 0,
        "orbs": 9,
    },
}


# ======================================================================
# LiveBackground
# ======================================================================

class LiveBackground:

    def __init__(self, parent, style="space"):

        self.parent = parent
        self.style = style if style in PRESETS else "space"
        self.preset = PRESETS[self.style]

        self.base = self.preset["base"]

        self.canvas = tk.Canvas(
            parent,
            bg=self.base,
            highlightthickness=0,
            bd=0
        )

        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)

        self.width = 1500
        self.height = 850

        self._running = True
        self._after_id = None
        self._frame = 0
        self._last = time.perf_counter()
        self._clock = 0.0

        self._sprites = []          # keep PhotoImage references alive
        self._glows = []
        self._stars = []
        self._bubbles = []
        self._orbs = []
        self._meteor = None
        self._next_meteor = 4.0

        self._pointer = (0.5, 0.5)

        self._build_glows()
        self._build_stars()
        self._build_bubbles()
        self._build_orbs()

        self.canvas.bind("<Configure>", self._on_resize)

        self._tick()

    # ------------------------------------------------------------------
    # build
    # ------------------------------------------------------------------

    def _build_glows(self):

        if not _HAS_PIL:
            return

        falloff = 1.8 if self.style == "glass" else 2.2

        for (cx, cy, ax, ay, px, py, size, color, peak) in self.preset["glows"]:

            try:
                sprite = _glow_sprite(size, color, peak, falloff)
            except Exception:
                continue

            item = self.canvas.create_image(
                0, 0, image=sprite, anchor="center"
            )

            self._sprites.append(sprite)

            self._glows.append({
                "id": item,
                "cx": cx, "cy": cy,
                "ax": ax, "ay": ay,
                "wx": 2 * math.pi / px,
                "wy": 2 * math.pi / py,
                "phase": random.uniform(0, 2 * math.pi),
            })

    def _build_stars(self):

        count = self.preset["stars"]

        if not count:
            return

        # depth 0 = far (small, slow, dim)   depth 2 = near
        palette = [
            [_mix(self.base, "#8A9BB2", k / 3) for k in (1, 2, 3, 2)],
            [_mix(self.base, "#A9BAD2", k / 3) for k in (1, 2, 3, 2)],
            [_mix(self.base, "#DCE8FA", k / 3) for k in (1, 2, 3, 2)],
        ]

        for _ in range(count):

            depth = random.choices([0, 1, 2], weights=[60, 30, 10])[0]

            size = (
                random.choice([0.6, 0.8, 1.0]) if depth == 0 else
                random.choice([1.0, 1.3, 1.6]) if depth == 1 else
                random.choice([1.8, 2.2, 2.6])
            )

            item = self.canvas.create_oval(
                0, 0, 0, 0, fill=palette[depth][0], outline=""
            )

            self._stars.append({
                "id": item,
                "nx": random.random(),
                "ny": random.random(),
                "depth": depth,
                "size": size,
                "speed": 0.0030 + depth * 0.0045,    # fraction of width / s
                "phase": random.uniform(0, 2 * math.pi),
                "rate": random.uniform(0.6, 2.2),
                "palette": palette[depth],
                "shade": 0,
            })

    def _build_bubbles(self):

        count = self.preset["bubbles"]

        for _ in range(count):

            radius = random.uniform(10, 46)

            ring = _mix(self.base, random.choice(
                ["#8FA2FF", "#7FE3F5", "#E7A6F5", "#FFFFFF"]
            ), random.uniform(0.18, 0.34))

            item = self.canvas.create_oval(
                0, 0, 0, 0, outline=ring, width=1
            )

            # tiny highlight on the upper-left of the bubble (specular)
            shine = self.canvas.create_arc(
                0, 0, 0, 0,
                start=110, extent=60,
                style="arc",
                outline=_mix(self.base, "#FFFFFF", 0.42),
                width=1
            )

            self._bubbles.append({
                "id": item,
                "shine": shine,
                "nx": random.random(),
                "ny": random.random(),
                "r": radius,
                "speed": random.uniform(0.004, 0.012),   # fraction of height / s
                "sway": random.uniform(0.01, 0.03),
                "phase": random.uniform(0, 2 * math.pi),
            })

    def _build_orbs(self):

        if not _HAS_PIL:
            return

        colors = ["#8FA2FF", "#7FE3F5", "#E7A6F5", "#A6F5D8"]

        for index in range(self.preset.get("orbs", 0)):

            size = random.choice([70, 96, 130, 170, 220])

            try:
                sprite = _orb_sprite(size, colors[index % len(colors)])
            except Exception:
                continue

            item = self.canvas.create_image(0, 0, image=sprite, anchor="center")

            self._sprites.append(sprite)

            self._orbs.append({
                "id": item,
                "nx": random.random(),
                "ny": random.random(),
                "speed": random.uniform(0.003, 0.009),
                "sway": random.uniform(0.015, 0.04),
                "phase": random.uniform(0, 2 * math.pi),
                "r": size / 2,
            })

    # ------------------------------------------------------------------
    # events
    # ------------------------------------------------------------------

    def _on_resize(self, event):

        if event.width > 1 and event.height > 1:
            self.width = event.width
            self.height = event.height

    # ------------------------------------------------------------------
    # animation
    # ------------------------------------------------------------------

    def _tick(self):

        if not self._running:
            return

        try:

            if not self.canvas.winfo_viewable():
                # minimised / hidden: do (almost) nothing
                self._last = time.perf_counter()
                self._after_id = self.canvas.after(300, self._tick)
                return

            now = time.perf_counter()
            dt = min(now - self._last, 0.25)
            self._last = now
            self._clock += dt
            self._frame += 1

            self._read_pointer()

            self._move_glows()

            if self._stars:
                self._move_stars(dt)
                self._twinkle()
                self._shooting_star(dt)

            if self._bubbles:
                self._move_bubbles(dt)

            if self._orbs:
                self._move_orbs(dt)

            self._after_id = self.canvas.after(
                int(1000 / FPS), self._tick
            )

        except tk.TclError:
            # window is being destroyed
            self._running = False

    def _read_pointer(self):

        try:
            px, py = self.canvas.winfo_pointerxy()
            rx = self.canvas.winfo_rootx()
            ry = self.canvas.winfo_rooty()

            nx = (px - rx) / max(self.width, 1)
            ny = (py - ry) / max(self.height, 1)

            nx = max(0.0, min(1.0, nx))
            ny = max(0.0, min(1.0, ny))

            # ease towards the pointer so it never jumps
            ox, oy = self._pointer
            self._pointer = (ox + (nx - ox) * 0.06, oy + (ny - oy) * 0.06)

        except tk.TclError:
            pass

    def _move_glows(self):

        w, h = self.width, self.height
        t = self._clock

        parallax_x = (self._pointer[0] - 0.5) * -28
        parallax_y = (self._pointer[1] - 0.5) * -18

        for glow in self._glows:

            x = (
                glow["cx"]
                + glow["ax"] * math.sin(t * glow["wx"] + glow["phase"])
            ) * w + parallax_x

            y = (
                glow["cy"]
                + glow["ay"] * math.cos(t * glow["wy"] + glow["phase"])
            ) * h + parallax_y

            self.canvas.coords(glow["id"], x, y)

    def _move_stars(self, dt):

        # move only on even frames (stars drift < 1 px per frame)
        if self._frame % 2:
            return

        w, h = self.width, self.height
        step = dt * 2

        px = (self._pointer[0] - 0.5)
        py = (self._pointer[1] - 0.5)

        for star in self._stars:

            star["nx"] -= star["speed"] * step

            if star["nx"] < -0.01:
                star["nx"] += 1.02
                star["ny"] = random.random()

            depth = star["depth"] + 1

            x = star["nx"] * w + px * -10 * depth
            y = star["ny"] * h + py * -6 * depth
            r = star["size"]

            self.canvas.coords(star["id"], x - r, y - r, x + r, y + r)

    def _twinkle(self):

        # touch only 1/4 of the stars each frame
        offset = self._frame % 4
        t = self._clock

        for index in range(offset, len(self._stars), 4):

            star = self._stars[index]

            level = (math.sin(t * star["rate"] + star["phase"]) + 1) / 2
            shade = min(3, int(level * 4))

            if shade != star["shade"]:
                star["shade"] = shade
                self.canvas.itemconfigure(
                    star["id"], fill=star["palette"][shade]
                )

    def _shooting_star(self, dt):

        if not self.preset["shooting"]:
            return

        w, h = self.width, self.height

        if self._meteor is None:

            if self._clock >= self._next_meteor:

                angle = math.radians(random.uniform(18, 34))

                self._meteor = {
                    "x": random.uniform(0.2, 0.9) * w,
                    "y": random.uniform(0.02, 0.35) * h,
                    "dx": math.cos(angle),
                    "dy": math.sin(angle),
                    "life": 0.0,
                    "ids": [
                        self.canvas.create_line(
                            0, 0, 0, 0, width=2 if i == 0 else 1,
                            fill=_mix(self.base, "#EAF2FF", 1 - i * 0.22)
                        )
                        for i in range(4)
                    ],
                }

            return

        m = self._meteor
        speed = 1100.0

        m["life"] += dt
        m["x"] += m["dx"] * speed * dt
        m["y"] += m["dy"] * speed * dt

        fade = max(0.0, 1.0 - m["life"] / 0.9)

        for i, item in enumerate(m["ids"]):

            start = (i + 1) * 26
            end = i * 26

            self.canvas.coords(
                item,
                m["x"] - m["dx"] * start, m["y"] - m["dy"] * start,
                m["x"] - m["dx"] * end, m["y"] - m["dy"] * end
            )

            self.canvas.itemconfigure(
                item,
                fill=_mix(self.base, "#EAF2FF", fade * (1 - i * 0.22))
            )

        if m["life"] >= 0.9 or m["x"] > w + 50 or m["y"] > h + 50:

            for item in m["ids"]:
                self.canvas.delete(item)

            self._meteor = None
            self._next_meteor = self._clock + random.uniform(7, 15)

    def _move_bubbles(self, dt):

        w, h = self.width, self.height
        t = self._clock

        for bubble in self._bubbles:

            bubble["ny"] -= bubble["speed"] * dt

            if bubble["ny"] < -0.1:
                bubble["ny"] = 1.1
                bubble["nx"] = random.random()

            x = (
                bubble["nx"]
                + bubble["sway"] * math.sin(t * 0.5 + bubble["phase"])
            ) * w

            y = bubble["ny"] * h
            r = bubble["r"]

            self.canvas.coords(bubble["id"], x - r, y - r, x + r, y + r)

            self.canvas.coords(
                bubble["shine"],
                x - r * 0.78, y - r * 0.78, x + r * 0.78, y + r * 0.78
            )

    def _move_orbs(self, dt):

        w, h = self.width, self.height
        t = self._clock

        for orb in self._orbs:

            orb["ny"] -= orb["speed"] * dt

            if orb["ny"] < -0.2:
                orb["ny"] = 1.2
                orb["nx"] = random.random()

            x = (orb["nx"] + orb["sway"] * math.sin(t * 0.35 + orb["phase"])) * w
            y = orb["ny"] * h

            self.canvas.coords(orb["id"], x, y)

    # ------------------------------------------------------------------
    # shutdown
    # ------------------------------------------------------------------

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
