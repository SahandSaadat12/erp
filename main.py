import os
import sys
import traceback
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image

from config import *
from style import setup_treeview
from paths import ICON_DIR
from utils.app_icon import apply_icon, install_for_all_windows, set_taskbar_identity
import database
from licensing import gate as license_gate
from db.connection import set_database_password, ensure_database_decrypted

from ui.backgrounds import LiveBackground

try:
    from ui.nebula import NebulaBackground
except Exception:                       # numpy missing -> old glass background
    NebulaBackground = None
from ui.splash import Splash

from ui.dashboard.dashboard import create_dashboard
from ui.projects.projects import create_projects
from ui.contracts.contracts import create_contracts
from ui.expenses.expenses import create_expenses
from ui.roadmap.roadmap import create_roadmap
from ui.documents.documents import create_documents
from ui.settings.settings import create_settings


# ==========================================
# Appearance  (must be set BEFORE any widget exists)
# ==========================================

ctk.set_appearance_mode(APPEARANCE)
ctk.set_default_color_theme("blue")

if GLASS_WIDGETS:
    from ui.glass import apply_glass_defaults
    apply_glass_defaults()


# ==========================================
# Icons
# ==========================================

ICON_SIZE = (24, 24)


def load_icon(filename, size=ICON_SIZE):

    path = os.path.join(ICON_DIR, filename)

    if not os.path.exists(path):
        return None

    try:

        image = Image.open(path).convert("RGBA")

        return ctk.CTkImage(
            light_image=image,
            dark_image=image,
            size=size
        )

    except Exception as error:

        print(f"Icon Load Error [{filename}]:", error)

        return None


def load_icons():

    return {
        "Dashboard": load_icon("dashboard.png"),
        "Projects": load_icon("projects.png"),
        "Contracts": load_icon("contracts.png"),
        "Expenses": load_icon("expenses.png"),
        "Documents": load_icon("documents.png"),
        "Roadmap": load_icon("roadmap.png"),
        "Settings": load_icon("settings.png"),
    }


# ==========================================
# Layout constants
# ==========================================

TAB_NAMES = [
    "Dashboard",
    "Projects",
    "Contracts",
    "Expenses",
    "Documents",
    "Roadmap",
]

# live themes: floating rounded panels with the animated background
# visible in the gaps.  Dark / Light keep the classic full-width layout.
if LIVE_BACKGROUND:
    MARGIN = 18
    PANEL_RADIUS = 18
    PANEL_BORDER_WIDTH = 1
else:
    MARGIN = 15
    PANEL_RADIUS = 12
    PANEL_BORDER_WIDTH = 0


# ==========================================
# Main
# ==========================================

def main():

    set_taskbar_identity()
    install_for_all_windows(CURRENT_THEME)

    app = ctk.CTk()
    apply_icon(app, CURRENT_THEME)       # themed title-bar / taskbar icon
    app.withdraw()
    app.attributes("-alpha", 0.0)

    app.title(APP_TITLE)
    app.configure(fg_color=BACKGROUND)

    screen_w = app.winfo_screenwidth()
    screen_h = app.winfo_screenheight()

    width = min(WIDTH, screen_w - 60)
    height = min(HEIGHT, screen_h - 100)

    app.geometry(
        f"{width}x{height}"
        f"+{(screen_w - width) // 2}+{max(0, (screen_h - height) // 2 - 20)}"
    )

    app.minsize(
        min(MIN_WIDTH, width),
        min(MIN_HEIGHT, height)
    )

    if NATIVE_GLASS:
        from ui.native_glass import apply_backdrop
        apply_backdrop(app, dark=(APPEARANCE == "Dark"))

    # ======================================
    # License gate: runs BEFORE the database is touched. Missing / invalid /
    # expired / wrong-machine / revoked licenses stop the ERP here (fail closed).
    # ======================================

    active_license = license_gate.run_startup_gate(app)

    if active_license is None:
        app.destroy()
        return

    license_gate.set_active_license(active_license)
    license_gate.LicenseMonitor(app).start()

    # ======================================
    # Database MUST exist before Login can query the users table.
    # This runs once, synchronously, before any window is shown.
    # ======================================

    try:
        database.setup_database()

    except Exception as error:
        from utils.app_logger import error as log_error
        log_error("Database startup error", exc_info=True)

        messagebox.showerror(
            "Startup error",
            "The database could not be opened or created.\n\n"
            "Please check the application log for details."
        )

        app.destroy()
        return

    state = {
        "background": None,
        "icons": {},
        "show_tab": None,
        "current_user": {},
    }

    # ======================================
    # Login  (must succeed before the rest of the app is built)
    # ======================================

    splash_holder = {}

    def start_after_login(user):

        state["current_user"] = user

        splash_holder["splash"] = Splash(app)

        app.after(80, run)

    from ui.login import LoginWindow
    LoginWindow(app, start_after_login)

    # ======================================
    # Start-up stages  (each one updates the splash; run AFTER login)
    # ======================================

    def stage_theme():

        setup_treeview()

        state["icons"] = load_icons()

        # created first => lowest in the stacking order
        if BACKGROUND_STYLE in ("nebula", "nebula_light") and NebulaBackground:
            state["background"] = NebulaBackground(app, BACKGROUND_STYLE)

        elif BACKGROUND_STYLE:
            style = "glass" if BACKGROUND_STYLE in ("nebula", "nebula_light") else BACKGROUND_STYLE
            state["background"] = LiveBackground(app, style)

    def stage_layout():
        build_layout(app, state)

    def stage_dashboard():
        state["show_tab"]("Dashboard")

    stages = [
        ("Applying theme", 15, 40, stage_theme),
        ("Building interface", 40, 75, stage_layout),
        ("Loading dashboard", 75, 97, stage_dashboard),
    ]

    # ======================================
    # Runner
    # ======================================

    def fail(error):

        try:
            splash_holder["splash"].window.destroy()
        except Exception:
            pass

        from utils.app_logger import error as log_error
        log_error("Application startup failed", exc_info=True)

        messagebox.showerror(
            "Startup error",
            "The application could not start.\n\n"
            "Please check the application log for details."
        )

        app.destroy()

    def run(index=0):

        if index >= len(stages):
            splash_holder["splash"].update_status("Ready", 100)
            wait_ready()
            return

        text, before, after, function = stages[index]

        splash_holder["splash"].update_status(text, before)

        # let the splash repaint, then do the (blocking) work
        def work():

            try:
                function()
            except Exception as error:
                fail(error)
                return

            splash_holder["splash"].update_status(text, after)

            # give the progress bar time to catch up
            app.after(140, run, index + 1)

        app.after(60, work)

    def wait_ready():

        if splash_holder["splash"].is_ready():
            reveal()
        else:
            app.after(30, wait_ready)

    def reveal():

        app.update_idletasks()

        app.attributes("-alpha", 1.0)
        app.deiconify()
        app.update_idletasks()

        splash_holder["splash"].lift()

        def done():
            app.lift()
            app.focus_force()

        splash_holder["splash"].finish(done)

    # ======================================
    # Close
    # ======================================

    def on_close():

        background = state["background"]

        if state.get("tint"):
            state["tint"].stop()

        if background is not None:
            background.stop()

        app.destroy()

    app.protocol("WM_DELETE_WINDOW", on_close)

    app.mainloop()


# ==========================================
# Layout
# ==========================================

def build_layout(app, state):

    icons = state["icons"]
    current_user = state["current_user"]

    # only modules enabled by the license are built / shown
    tab_names = license_gate.filter_tabs(TAB_NAMES)

    app.grid_rowconfigure(2, weight=1)
    app.grid_columnconfigure(0, weight=1)

    classic = not LIVE_BACKGROUND

    # --------------------------------------
    # Header
    # --------------------------------------

    header = ctk.CTkFrame(
        app,
        fg_color=HEADER,
        corner_radius=0 if classic else PANEL_RADIUS,
        border_width=PANEL_BORDER_WIDTH,
        border_color=PANEL_BORDER,
        height=70
    )

    header.grid(
        row=0,
        column=0,
        sticky="ew",
        padx=0 if classic else MARGIN,
        pady=0 if classic else (MARGIN, 0)
    )

    header.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        header,
        text=APP_TITLE,
        text_color=TEXT,
        font=("Segoe UI", 28, "bold")
    ).grid(
        row=0,
        column=0,
        padx=22,
        pady=14,
        sticky="w"
    )

    def open_settings():

        if not database.has_permission(current_user, "settings.view"):
            messagebox.showwarning(
                "Settings", "You don't have permission to open Settings."
            )
            return

        win = ctk.CTkToplevel(app)

        win.title("Settings")
        win.geometry("1000x720")
        win.transient(app)
        win.grab_set()

        create_settings(win, current_user)

    ctk.CTkButton(
        header,
        text="Settings",
        image=icons.get("Settings"),
        compound="left",
        width=140,
        height=42,
        corner_radius=12,
        fg_color=CARD,
        hover_color=CARD_HOVER,
        text_color=TEXT,
        font=("Segoe UI", 16, "bold"),
        command=open_settings
    ).grid(
        row=0,
        column=1,
        padx=20
    )

    # --------------------------------------
    # Navigation (icons + text)
    # --------------------------------------

    nav = ctk.CTkFrame(
        app,
        fg_color=HEADER,
        corner_radius=PANEL_RADIUS,
        border_width=PANEL_BORDER_WIDTH,
        border_color=PANEL_BORDER
    )

    nav.grid(
        row=1,
        column=0,
        sticky="ew",
        padx=MARGIN,
        pady=(MARGIN, 0)
    )

    # --------------------------------------
    # Content panel
    # --------------------------------------

    container = ctk.CTkFrame(
        app,
        fg_color=PANEL,
        corner_radius=PANEL_RADIUS,
        border_width=PANEL_BORDER_WIDTH,
        border_color=PANEL_BORDER
    )

    container.grid(
        row=2,
        column=0,
        sticky="nsew",
        padx=MARGIN,
        pady=MARGIN
    )

    container.grid_rowconfigure(0, weight=1)
    container.grid_columnconfigure(0, weight=1)

    frames = {}

    for name in tab_names:

        frame = ctk.CTkFrame(container, fg_color="transparent")

        frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        frame.grid_remove()

        frames[name] = frame

    builders = {
        "Dashboard": lambda f: create_dashboard(f),
        "Projects": lambda f: create_projects(f, database, current_user),
        "Contracts": lambda f: create_contracts(f, database, current_user),
        "Expenses": lambda f: create_expenses(f, current_user),
        "Documents": lambda f: create_documents(f, current_user),
        "Roadmap": lambda f: create_roadmap(f, current_user),
    }

    buttons = {}

    built = {}              # tab -> data version it was built with
    current = {"name": None}

    def show_tab(name):

        background = state.get("background")

        version = database.get_data_version()

        # leaving a tab: it kept itself up to date while it was open
        if current["name"] in built:
            built[current["name"]] = version

        # 1) build while the frame is NOT mapped (much cheaper than building
        #    widget by widget on screen), and only if the data changed
        if built.get(name) != version:

            if background is not None and hasattr(background, "hold"):
                background.hold(0.5)

            builders[name](frames[name])
            built[name] = version

        # 2) switch in one go
        for key, frame in frames.items():
            if key != name:
                frame.grid_remove()

        for key, button in buttons.items():

            active = key == name

            button.configure(
                fg_color=BLUE if active else "transparent",
                hover_color=BLUE_HOVER if active else CARD_HOVER,
                text_color=ON_ACCENT if active else TEXT
            )

        frames[name].grid()

        current["name"] = name

    for column, name in enumerate(tab_names):

        nav.grid_columnconfigure(column, weight=1)

        button = ctk.CTkButton(
            nav,
            text=name,
            image=icons.get(name),
            compound="left",
            height=44,
            corner_radius=12,
            fg_color="transparent",
            hover_color=CARD_HOVER,
            text_color=TEXT,
            font=("Segoe UI", 16, "bold"),
            command=lambda n=name: show_tab(n)
        )

        button.grid(
            row=0,
            column=column,
            sticky="ew",
            padx=6,
            pady=6
        )

        buttons[name] = button

    state["show_tab"] = show_tab

    # glass panels pick up the colour of the nebula behind them
    background = state.get("background")

    if GLASS_WIDGETS and background is not None and hasattr(background, "mean_color"):

        from ui.glass import GlassTint

        state["tint"] = GlassTint(
            background,
            [
                (header, HEADER, 0.9),
                (nav, HEADER, 0.9),
                (container, PANEL, 0.5),
            ]
        )


# ==========================================
# Start
# ==========================================

if __name__ == "__main__":

    main()
