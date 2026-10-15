import json

from paths import (
    SETTINGS_FILE,
    DB_PATH,
    BACKUP_DIR,
    DOCUMENTS_DIR,
    ICON_DIR,
)
from themes import THEMES


# ===============================
# Window
# ===============================

APP_TITLE = "ERP Project Management"

WIDTH = 1500
HEIGHT = 850

MIN_WIDTH = 1200
MIN_HEIGHT = 700


# ===============================
# Settings file  (theme, currency ...)
# ===============================

DEFAULT_THEME = "Dark"
DEFAULT_CURRENCY = "Toman"


def load_settings():

    try:

        with open(
            SETTINGS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if isinstance(data, dict):
            return data

    except Exception:
        pass

    return {}


def save_setting(key, value):

    settings = load_settings()

    settings[key] = value

    with open(
        SETTINGS_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            settings,
            file,
            indent=4,
            ensure_ascii=False
        )


def load_saved_theme():

    theme = load_settings().get("theme", DEFAULT_THEME)

    # old name used before "Liquid Glass" existed
    if theme == "Glass":
        theme = "Liquid Glass"

    return theme if theme in THEMES else DEFAULT_THEME


CURRENT_THEME = load_saved_theme()

THEME = THEMES[CURRENT_THEME]

GLASS_TINT_BASE = THEME["PANEL"]      # colour tinted-glass buttons are mixed on

# ---- experimental: real Windows 11 acrylic (see ui/native_glass.py) ----
NATIVE_GLASS = False

if THEME.get("GLASS_WIDGETS") and load_settings().get("native_glass"):

    from ui.native_glass import is_supported, KEY

    if is_supported():

        NATIVE_GLASS = True

        THEME = {
            **THEME,
            "BACKGROUND_STYLE": None,
            "BACKGROUND": KEY,
            "PANEL": KEY,
            "HEADER": KEY,
            "CARD": KEY,
            "TREE_BACKGROUND": THEME["TREE_BACKGROUND"],
        }

CURRENCY = str(
    load_settings().get("currency", DEFAULT_CURRENCY)
)


# ===============================
# Appearance
# ===============================

APPEARANCE = THEME["APPEARANCE"]

BACKGROUND_STYLE = THEME["BACKGROUND_STYLE"]   # None | "space" | "glass"

LIVE_BACKGROUND = BACKGROUND_STYLE is not None or NATIVE_GLASS

GLASS_WIDGETS = bool(THEME.get("GLASS_WIDGETS", False))

GLASS_FIELD = THEME.get("GLASS_FIELD", THEME["CARD"])
GLASS_EDGE = THEME.get("GLASS_EDGE", THEME["BORDER"])


# ===============================
# Colors
# ===============================

BACKGROUND = THEME["BACKGROUND"]

PANEL = THEME["PANEL"]
PANEL_BORDER = THEME["PANEL_BORDER"]

CARD = THEME["CARD"]
CARD_HOVER = THEME["CARD_HOVER"]

HEADER = THEME["HEADER"]
HEADER_ACTIVE = THEME["HEADER_ACTIVE"]

BORDER = THEME["BORDER"]
TRACK = THEME["TRACK"]

BLUE = THEME["BLUE"]
GREEN = THEME["GREEN"]
RED = THEME["RED"]
ORANGE = THEME["ORANGE"]
YELLOW = THEME["YELLOW"]

TEXT = THEME["TEXT"]
TEXT2 = THEME["TEXT2"]


# ===============================
# Button Colors
# ===============================

BLUE_HOVER = THEME["BLUE_HOVER"]
GREEN_HOVER = THEME["GREEN_HOVER"]

DELETE = THEME["DELETE"]
DELETE_HOVER = THEME["DELETE_HOVER"]

VIEW = THEME["VIEW"]
VIEW_HOVER = THEME["VIEW_HOVER"]

NEUTRAL = THEME["NEUTRAL"]
NEUTRAL_HOVER = THEME["NEUTRAL_HOVER"]


# ===============================
# Splash
# ===============================

SPLASH_BG = THEME["SPLASH_BG"]
SPLASH_GLOW = THEME["SPLASH_GLOW"]
SPLASH_ACCENT = THEME["SPLASH_ACCENT"]
SPLASH_TEXT = THEME["SPLASH_TEXT"]


# ===============================
# Fonts
# ===============================

FONT_TITLE = ("Segoe UI", 28, "bold")

FONT_NORMAL = ("Segoe UI", 15)

FONT_TREE = ("Segoe UI", 11)

FONT_TREE_HEADER = ("Segoe UI", 11, "bold")

FONT_TAB = ("Segoe UI", 18, "bold")

FONT_CARD_TITLE = ("Segoe UI", 17)

FONT_CARD_VALUE = ("Segoe UI", 36, "bold")

FONT_PROGRESS = ("Segoe UI", 20, "bold")

FONT_PERCENT = ("Segoe UI", 24, "bold")

FONT_PERSIAN = ("Tahoma", 13)

FONT_PERSIAN_BOLD = ("Tahoma", 14, "bold")


# ===============================
# Treeview
# ===============================

TREE_ROW_HEIGHT = 34

TREE_FONT = ("Segoe UI", 11)

TREE_HEADER_FONT = ("Segoe UI", 11, "bold")

TREE_BACKGROUND = THEME["TREE_BACKGROUND"]

TREE_FOREGROUND = THEME["TREE_FOREGROUND"]

TREE_SELECTED = THEME["TREE_SELECTED"]

TREE_HEADER_BACKGROUND = THEME["TREE_HEADER_BACKGROUND"]

TREE_HEADER_FOREGROUND = THEME["TREE_HEADER_FOREGROUND"]


# ===============================
# Misc
# ===============================

ON_ACCENT = "#FFFFFF"      # text drawn on top of BLUE / GREEN / RED buttons
