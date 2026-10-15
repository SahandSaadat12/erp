# ==========================================
# ERP Themes
#
# Every colour used by the UI must come from here
# (no hard-coded hex values inside ui/*).
#
# Extra keys compared to the old version:
#   PANEL / PANEL_BORDER  floating surface that sits on the live background
#   CARD_HOVER            hover colour of cards, nav buttons, segmented tabs
#   TRACK                 empty part of progress bars
#   HEADER_ACTIVE         hovered tree heading
#   NEUTRAL / NEUTRAL_HOVER   secondary buttons
#   APPEARANCE            "Dark" / "Light"  -> customtkinter appearance mode
#   BACKGROUND_STYLE      None | "space" | "glass"  (animated background)
#   SPLASH_*              splash screen palette
# ==========================================


# ==========================================
# Dark Theme
# ==========================================

DARK_THEME = {

    "APPEARANCE": "Dark",
    "BACKGROUND_STYLE": None,

    "BACKGROUND": "#1B1F27",
    "PANEL": "#1B1F27",
    "PANEL_BORDER": "#1B1F27",
    "CARD": "#242A38",
    "CARD_HOVER": "#31394A",
    "HEADER": "#202534",
    "HEADER_ACTIVE": "#2B3140",
    "BORDER": "#32394A",
    "TRACK": "#30394B",

    "BLUE": "#3B82F6",
    "GREEN": "#22C55E",
    "RED": "#EF4444",
    "ORANGE": "#F59E0B",
    "YELLOW": "#EAB308",

    "TEXT": "#FFFFFF",
    "TEXT2": "#BFC7D5",

    "BLUE_HOVER": "#2563EB",
    "GREEN_HOVER": "#16A34A",

    "DELETE": "#DC2626",
    "DELETE_HOVER": "#B91C1C",

    "VIEW": "#4B5563",
    "VIEW_HOVER": "#374151",

    "NEUTRAL": "#374151",
    "NEUTRAL_HOVER": "#1F2937",

    "TREE_BACKGROUND": "#242A38",
    "TREE_FOREGROUND": "#FFFFFF",
    "TREE_SELECTED": "#3B82F6",
    "TREE_HEADER_BACKGROUND": "#202534",
    "TREE_HEADER_FOREGROUND": "#FFFFFF",

    "SPLASH_BG": "#10131A",
    "SPLASH_GLOW": ["#10131A", "#131824", "#171E2D", "#1B2437", "#1F2A42"],
    "SPLASH_ACCENT": "#3B82F6",
    "SPLASH_TEXT": "#8EA4C3",
}


# ==========================================
# Light Theme
# ==========================================

LIGHT_THEME = {

    "APPEARANCE": "Light",
    "BACKGROUND_STYLE": None,

    "BACKGROUND": "#F3F4F6",
    "PANEL": "#F3F4F6",
    "PANEL_BORDER": "#F3F4F6",
    "CARD": "#FFFFFF",
    "CARD_HOVER": "#E5E7EB",
    "HEADER": "#E5E7EB",
    "HEADER_ACTIVE": "#D1D5DB",
    "BORDER": "#D1D5DB",
    "TRACK": "#D1D5DB",

    "BLUE": "#2563EB",
    "GREEN": "#16A34A",
    "RED": "#DC2626",
    "ORANGE": "#D97706",
    "YELLOW": "#CA8A04",

    "TEXT": "#111827",
    "TEXT2": "#6B7280",

    "BLUE_HOVER": "#1D4ED8",
    "GREEN_HOVER": "#15803D",

    "DELETE": "#DC2626",
    "DELETE_HOVER": "#B91C1C",

    "VIEW": "#6B7280",
    "VIEW_HOVER": "#4B5563",

    "NEUTRAL": "#6B7280",
    "NEUTRAL_HOVER": "#4B5563",

    "TREE_BACKGROUND": "#FFFFFF",
    "TREE_FOREGROUND": "#111827",
    "TREE_SELECTED": "#2563EB",
    "TREE_HEADER_BACKGROUND": "#E5E7EB",
    "TREE_HEADER_FOREGROUND": "#111827",

    "SPLASH_BG": "#EEF1F6",
    "SPLASH_GLOW": ["#EEF1F6", "#E8ECF4", "#E1E7F2", "#DAE2F0", "#D3DDEE"],
    "SPLASH_ACCENT": "#2563EB",
    "SPLASH_TEXT": "#4B5563",
}


# ==========================================
# Space Theme  (live starfield + nebula)
# ==========================================

SPACE_THEME = {

    "APPEARANCE": "Dark",
    "BACKGROUND_STYLE": "space",

    "BACKGROUND": "#050609",
    "PANEL": "#0A0D13",
    "PANEL_BORDER": "#1C222C",
    "CARD": "#11141A",
    "CARD_HOVER": "#1A1F29",
    "HEADER": "#0B0E13",
    "HEADER_ACTIVE": "#1A1F29",
    "BORDER": "#252A32",
    "TRACK": "#1E242E",

    "BLUE": "#6B8AA8",
    "GREEN": "#7FA58D",
    "RED": "#B87878",
    "ORANGE": "#B49A72",
    "YELLOW": "#B8A878",

    "TEXT": "#E4E7EA",
    "TEXT2": "#9AA2AD",

    "BLUE_HOVER": "#5C7894",
    "GREEN_HOVER": "#6F927C",

    "DELETE": "#A86666",
    "DELETE_HOVER": "#8D5555",

    "VIEW": "#444A53",
    "VIEW_HOVER": "#555C66",

    "NEUTRAL": "#3A404A",
    "NEUTRAL_HOVER": "#2C313A",

    "TREE_BACKGROUND": "#11141A",
    "TREE_FOREGROUND": "#E4E7EA",
    "TREE_SELECTED": "#35485A",
    "TREE_HEADER_BACKGROUND": "#0B0E13",
    "TREE_HEADER_FOREGROUND": "#E4E7EA",

    "SPLASH_BG": "#070A11",
    "SPLASH_GLOW": ["#070A11", "#09101D", "#0D192B", "#132A47", "#173354"],
    "SPLASH_ACCENT": "#3B82F6",
    "SPLASH_TEXT": "#8EA4C3",
}


# ==========================================
# Liquid Glass Theme  (live aurora + frosted panels)
# ==========================================

GLASS_THEME = {

    "APPEARANCE": "Dark",
    "BACKGROUND_STYLE": "glass",

    "BACKGROUND": "#0A0E1F",
    "PANEL": "#141B33",
    "PANEL_BORDER": "#3A4570",
    "CARD": "#1B2342",
    "CARD_HOVER": "#273259",
    "HEADER": "#18203D",
    "HEADER_ACTIVE": "#2A3563",
    "BORDER": "#3D4A7A",
    "TRACK": "#2A3358",

    "BLUE": "#6C9BFF",
    "GREEN": "#4ADE9B",
    "RED": "#FB7185",
    "ORANGE": "#FBBF4A",
    "YELLOW": "#FDE047",

    "TEXT": "#F5F7FF",
    "TEXT2": "#B4BEE0",

    "BLUE_HOVER": "#527FE6",
    "GREEN_HOVER": "#35C685",

    "DELETE": "#E5566E",
    "DELETE_HOVER": "#C9415A",

    "VIEW": "#4A5686",
    "VIEW_HOVER": "#5C6AA0",

    "NEUTRAL": "#3A4672",
    "NEUTRAL_HOVER": "#4A5890",

    "TREE_BACKGROUND": "#1B2342",
    "TREE_FOREGROUND": "#F5F7FF",
    "TREE_SELECTED": "#4B6FD6",
    "TREE_HEADER_BACKGROUND": "#18203D",
    "TREE_HEADER_FOREGROUND": "#F5F7FF",

    "SPLASH_BG": "#0A0E1F",
    "SPLASH_GLOW": ["#0A0E1F", "#10143A", "#1A1650", "#2A1E6E", "#3B2A92"],
    "SPLASH_ACCENT": "#8B7CFF",
    "SPLASH_TEXT": "#B4BEE0",
}


# ==========================================
# Liquid Glass 2  (frosted widgets everywhere)
# ==========================================

GLASS2_THEME = {

    "APPEARANCE": "Dark",
    "BACKGROUND_STYLE": "nebula",
    "GLASS_WIDGETS": True,

    "BACKGROUND": "#060916",
    "PANEL": "#141B40",
    "PANEL_BORDER": "#404D85",
    "CARD": "#1D254D",
    "CARD_HOVER": "#26305D",
    "HEADER": "#161E43",
    "HEADER_ACTIVE": "#212A53",
    "BORDER": "#394579",
    "TRACK": "#242D59",

    "GLASS_FIELD": "#1F2851",
    "GLASS_EDGE": "#485590",

    "BLUE": "#5B8CFF",
    "GREEN": "#3DDC97",
    "RED": "#FF6B86",
    "ORANGE": "#FFB84D",
    "YELLOW": "#FFE066",

    "TEXT": "#F7F9FF",
    "TEXT2": "#B9C3EA",

    "BLUE_HOVER": "#7BA2FF",
    "GREEN_HOVER": "#63E8AF",

    "DELETE": "#E8546F",
    "DELETE_HOVER": "#FF7490",

    "VIEW": "#4A5890",
    "VIEW_HOVER": "#6272B8",

    "NEUTRAL": "#36437E",
    "NEUTRAL_HOVER": "#4A5A9E",

    "TREE_BACKGROUND": "#1A224A",
    "TREE_FOREGROUND": "#F7F9FF",
    "TREE_SELECTED": "#3E5BB8",
    "TREE_HEADER_BACKGROUND": "#222A55",
    "TREE_HEADER_FOREGROUND": "#F7F9FF",

    "SPLASH_BG": "#080C1C",
    "SPLASH_GLOW": ["#080C1C", "#10154A", "#1C1A70", "#2F2392", "#4630B8"],
    "SPLASH_ACCENT": "#8FA2FF",
    "SPLASH_TEXT": "#B9C3EA",
}


# ==========================================
# Liquid Glass Light  (bright pastel aurora, Apple-style frosted panes)
# ==========================================

GLASS_LIGHT_THEME = {

    "APPEARANCE": "Light",
    "BACKGROUND_STYLE": "nebula_light",
    "GLASS_WIDGETS": True,

    "BACKGROUND": "#ECF1FB",
    "PANEL": "#F7F9FE",
    "PANEL_BORDER": "#FFFFFF",
    "CARD": "#FCFDFF",
    "CARD_HOVER": "#E6EDFC",
    "HEADER": "#F4F7FD",
    "HEADER_ACTIVE": "#E1E9FA",
    "BORDER": "#D5DEF2",
    "TRACK": "#DDE5F6",

    "GLASS_FIELD": "#FFFFFF",
    "GLASS_EDGE": "#CBD6EE",

    "BLUE": "#2F6BFF",
    "GREEN": "#17A864",
    "RED": "#E5484D",
    "ORANGE": "#F08C00",
    "YELLOW": "#D9A400",

    "TEXT": "#0F172A",
    "TEXT2": "#566282",

    "BLUE_HOVER": "#1F55D6",
    "GREEN_HOVER": "#118A52",

    "DELETE": "#E5484D",
    "DELETE_HOVER": "#C93A3F",

    "VIEW": "#7C89A8",
    "VIEW_HOVER": "#66739A",

    "NEUTRAL": "#8793B0",
    "NEUTRAL_HOVER": "#6E7A99",

    "TREE_BACKGROUND": "#FBFCFF",
    "TREE_FOREGROUND": "#0F172A",
    "TREE_SELECTED": "#BFD1FF",
    "TREE_HEADER_BACKGROUND": "#E9EFFB",
    "TREE_HEADER_FOREGROUND": "#0F172A",

    "SPLASH_BG": "#EEF2FA",
    "SPLASH_GLOW": ["#EEF2FA", "#E8EEFB", "#E0E8FA", "#D8E2F9", "#CFDCF8"],
    "SPLASH_ACCENT": "#2F6BFF",
    "SPLASH_TEXT": "#566282",
}


# ==========================================
# Available Themes
# ==========================================

THEMES = {
    "Dark": DARK_THEME,
    "Light": LIGHT_THEME,
    "Space": SPACE_THEME,
    "Liquid Glass": GLASS_THEME,
    "Liquid Glass 2": GLASS2_THEME,
    "Liquid Glass Light": GLASS_LIGHT_THEME,
}
