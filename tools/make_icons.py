"""
Generates one Windows .ico per theme (icons/app_<Theme>.ico) + icons/app.ico
(the static icon baked into the .exe file).  Colours come straight from
themes.py, so a new theme only needs `python tools/make_icons.py` again.
"""
import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from themes import THEMES  # noqa: E402

S = 1024  # master canvas, downsampled for crisp edges


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def gradient(c1, c2):
    img = Image.new("RGB", (S, S))
    px = img.load()
    for y in range(S):
        for x in range(S):
            px[x, y] = mix(c1, c2, (x + y) / (2 * S - 2))
    return img


def rounded_mask(size, radius, inset=0):
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle(
        [inset, inset, size - 1 - inset, size - 1 - inset], radius, fill=255)
    return m


def make(theme_name, theme):
    light = theme["APPEARANCE"] == "Light"
    glow = theme["SPLASH_GLOW"]
    if light:
        c1, c2 = rgb("#FFFFFF"), rgb(glow[-1])
    else:
        c1, c2 = rgb(theme["SPLASH_BG"]), rgb(glow[-1])
        c2 = mix(c2, rgb(theme["SPLASH_ACCENT"]), 0.35)

    bg = gradient(c1, c2).convert("RGBA")
    d = ImageDraw.Draw(bg)

    # decorative stars for the Space theme
    if theme["BACKGROUND_STYLE"] == "space":
        rnd = random.Random(7)
        for _ in range(38):
            x, y, r = rnd.randint(40, S - 40), rnd.randint(40, S - 40), rnd.choice((3, 4, 6, 8))
            d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, rnd.randint(110, 230)))

    # three ascending bars + trend line
    accent = [rgb(theme["BLUE"]), rgb(theme["GREEN"]), rgb(theme["ORANGE"])]
    base_y = int(S * 0.76)
    bar_w = int(S * 0.15)
    gap = int(S * 0.065)
    heights = [0.26, 0.40, 0.56]
    total = 3 * bar_w + 2 * gap
    x0 = (S - total) // 2
    pts = []
    for i, (col, h) in enumerate(zip(accent, heights)):
        x = x0 + i * (bar_w + gap)
        top = base_y - int(S * h)
        # soft shadow
        sh = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle(
            [x + 10, top + 18, x + bar_w + 10, base_y + 18], 34, fill=(0, 0, 0, 90))
        bg = Image.alpha_composite(bg, sh.filter(ImageFilter.GaussianBlur(16)))
        d = ImageDraw.Draw(bg)
        d.rounded_rectangle([x, top, x + bar_w, base_y], 34, fill=col + (255,))
        d.rounded_rectangle([x + 14, top + 10, x + bar_w // 2, top + 60], 16,
                            fill=mix(col, (255, 255, 255), 0.35) + (150,))
        pts.append((x + bar_w // 2, top - int(S * 0.07)))

    # baseline
    line_col = (30, 41, 59, 255) if light else (255, 255, 255, 235)
    d.rounded_rectangle([x0 - 30, base_y + 28, x0 + total + 30, base_y + 52], 12,
                        fill=line_col[:3] + (140,))

    # trend line with dots
    tcol = (30, 41, 59, 255) if light else (255, 255, 255, 255)
    d.line(pts, fill=tcol, width=22, joint="curve")
    for p in pts:
        d.ellipse([p[0] - 24, p[1] - 24, p[0] + 24, p[1] + 24], fill=tcol)
        d.ellipse([p[0] - 11, p[1] - 11, p[0] + 11, p[1] + 11],
                  fill=mix(c1, c2, 0.5) + (255,))

    # glass sheen on glass themes
    if theme.get("GLASS_WIDGETS") or theme["BACKGROUND_STYLE"] in ("glass", "nebula", "nebula_light"):
        sheen = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        ImageDraw.Draw(sheen).ellipse([-S * 0.3, -S * 0.75, S * 1.3, S * 0.42],
                                      fill=(255, 255, 255, 46 if not light else 120))
        bg = Image.alpha_composite(bg, sheen)

    # rounded-square clip + thin rim
    radius = int(S * 0.22)
    icon = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    icon.paste(bg, (0, 0), rounded_mask(S, radius))
    rim = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(rim).rounded_rectangle(
        [3, 3, S - 4, S - 4], radius,
        outline=(255, 255, 255, 70) if not light else (15, 23, 42, 60), width=7)
    return Image.alpha_composite(icon, rim)


def main():
    out = os.path.join(ROOT, "icons")
    os.makedirs(out, exist_ok=True)
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    for name, theme in THEMES.items():
        img = make(name, theme)
        safe = name.replace(" ", "_")
        img.save(os.path.join(out, f"app_{safe}.ico"), sizes=sizes)
        img.resize((256, 256), Image.LANCZOS).save(os.path.join(out, f"app_{safe}.png"))
        if name == "Dark":
            img.save(os.path.join(out, "app.ico"), sizes=sizes)
        print("ok", name)


if __name__ == "__main__":
    main()
