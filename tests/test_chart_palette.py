import unittest
from tests.helpers import *                       # noqa
from ui.chart_palette import PALETTE, OTHER, distinct_colors, color_for


def lum(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


class PaletteTests(unittest.TestCase):
    def test_size_and_uniqueness(self):
        self.assertGreaterEqual(len(PALETTE), 12)
        self.assertEqual(len(set(c.lower() for c in PALETTE)), len(PALETTE))

    def test_readable_on_dark_theme_cards(self):
        import themes
        for name, theme in themes.THEMES.items():
            if theme["APPEARANCE"] != "Dark":
                continue
            for bg in (theme["CARD"], theme["BACKGROUND"]):
                for c in PALETTE:
                    self.assertGreaterEqual(contrast(c, bg), 3.0, (name, bg, c))

    def test_deterministic_across_calls(self):
        keys = ["Materials", "Labor", "Transport", "Permits", "Other"]
        self.assertEqual(distinct_colors(keys, fixed={"Other": OTHER}),
                         distinct_colors(list(keys), fixed={"Other": OTHER}))

    def test_stable_hash_not_python_hash(self):
        # fixed expectation: would differ between interpreter runs if hash() were used
        self.assertEqual(color_for("Materials"), color_for("Materials"))
        import subprocess, sys, os
        code = "from ui.chart_palette import color_for;print(color_for('Materials'))"
        env = {**os.environ, "PYTHONHASHSEED": "random"}
        outs = {subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env,
                               cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))).stdout
                for _ in range(3)}
        self.assertEqual(len(outs), 1)

    def test_visible_keys_never_share_a_colour(self):
        for n in range(1, len(PALETTE) + 1):
            keys = [f"Category {i}" for i in range(n)]
            cols = distinct_colors(keys)
            self.assertEqual(len(set(c.lower() for c in cols.values())), n, n)

    def test_more_keys_than_palette_still_deterministic_and_unique(self):
        keys = [f"phase-{i}" for i in range(40)]
        a, b = distinct_colors(keys), distinct_colors(keys)
        self.assertEqual(a, b)
        self.assertEqual(len(a), 40)
        self.assertEqual(len(set(c.lower() for c in a.values())), 40)

    def test_other_is_grey_and_does_not_consume_palette(self):
        cols = distinct_colors(["A", "Other"], fixed={"Other": OTHER})
        self.assertEqual(cols["Other"], OTHER)
        self.assertNotEqual(cols["A"], OTHER)

    def test_semantic_status_duplicates_are_separated(self):
        blue = PALETTE[0]
        cols = distinct_colors(["Open", "In Progress"], preferred={"Open": blue, "In Progress": blue})
        self.assertEqual(cols["Open"], blue)
        self.assertNotEqual(cols["In Progress"].lower(), blue.lower())

    def test_same_name_same_colour_when_no_collision(self):
        a = distinct_colors(["Materials", "Labor"])["Materials"]
        b = distinct_colors(["Materials"])["Materials"]
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
