import os
import sqlite3
from datetime import datetime

import customtkinter as ctk
from tkinter import messagebox, filedialog

from config import *
from .archive import create_archive
from .lists import create_lists
from .history import create_history
from utils.restart import restart_app
import database as db


# ==========================================
# Save Theme
# ==========================================

def save_theme(theme_name):
    save_setting("theme", theme_name)


# ==========================================
# Database Backup
# ==========================================

def backup_database():
    try:
        from db.backup import create_backup
        backup_path = create_backup()
        messagebox.showinfo(
            "Database Backup",
            "Database backup created and integrity-checked successfully.\n\n"
            f"{backup_path}"
        )
    except Exception as error:
        messagebox.showerror("Database Backup", f"Backup failed.\n\n{error}")


def restore_database_from_file():
    """Restore a selected SQLite backup after explicit confirmation."""
    backup_path = filedialog.askopenfilename(
        title="Select ERP database backup",
        initialdir=BACKUP_DIR,
        filetypes=[("SQLite database", "*.db"), ("All files", "*.*")],
    )
    if not backup_path:
        return

    confirmed = messagebox.askyesno(
        "Restore Database",
        "This replaces the current database with the selected backup.\n"
        "A safety backup of the current database will be created first.\n\n"
        "Close other ERP instances before continuing. Continue?",
        icon="warning",
    )
    if not confirmed:
        return

    try:
        from db.backup import restore_database
        result = restore_database(backup_path)
        messagebox.showinfo(
            "Restore Complete",
            "Database restored successfully. Restart the ERP before continuing.\n\n"
            f"Safety backup: {result.get('safety_backup') or 'No prior database existed'}",
        )
    except Exception as error:
        messagebox.showerror("Restore Failed", f"The database was not restored.\n\n{error}")

# ==========================================
# Settings
# ==========================================

def create_settings(parent, current_user=None):

    # ==========================================
    # Clear Parent
    # ==========================================

    for widget in parent.winfo_children():
        widget.destroy()

    for _row in range(8):
        parent.grid_rowconfigure(_row, weight=0)

    parent.grid_columnconfigure(
        0,
        weight=1
    )

    parent.grid_rowconfigure(
        1,
        weight=1
    )

    # ==========================================
    # Title
    # ==========================================

    title = ctk.CTkLabel(
        parent,
        text="Settings ⚙",
        font=("Segoe UI", 28, "bold"),
        text_color=TEXT
    )

    title.grid(
        row=0,
        column=0,
        sticky="w",
        padx=20,
        pady=(10, 15)
    )

    # ==========================================
    # Scrollable Settings
    # ==========================================

    settings_frame = ctk.CTkScrollableFrame(
        parent,
        fg_color="transparent"
    )

    settings_frame.grid(
        row=1,
        column=0,
        sticky="nsew",
        padx=5,
        pady=(0, 5)
    )

    settings_frame.grid_columnconfigure(
        0,
        weight=1
    )

    settings_frame.grid_columnconfigure(
        1,
        weight=1
    )

    # ==========================================
    # Appearance
    # ==========================================

    appearance = ctk.CTkFrame(
        settings_frame,
        fg_color=CARD,
        border_width=1,
        border_color=BORDER,
        corner_radius=12
    )

    appearance.grid(
        row=0,
        column=0,
        sticky="nsew",
        padx=(15, 7),
        pady=5
    )

    ctk.CTkLabel(
        appearance,
        text="🎨 Appearance",
        font=("Segoe UI", 20, "bold"),
        text_color=TEXT
    ).pack(
        anchor="w",
        padx=20,
        pady=(20, 15)
    )

    ctk.CTkLabel(
        appearance,
        text="Theme",
        font=("Segoe UI", 13),
        text_color=TEXT2
    ).pack(
        anchor="w",
        padx=20
    )

    theme = ctk.CTkComboBox(
        appearance,
        values=list(THEMES),
        width=180
    )

    theme.set(
        CURRENT_THEME
    )

    theme.pack(
        anchor="w",
        padx=20,
        pady=(5, 15)
    )

    # ==========================================
    # Apply Theme
    # ==========================================

    def apply_theme():

        selected_theme = theme.get()

        save_theme(
            selected_theme
        )

        if selected_theme == CURRENT_THEME:
            return

        if messagebox.askyesno(
            "Theme",
            f"Theme '{selected_theme}' has been saved.\n\n"
            "The application must restart to apply it.\n"
            "Restart now?"
        ):
            restart_app()

    ctk.CTkButton(
        appearance,
        text="Apply Theme",
        width=180,
        height=38,
        fg_color=BLUE,
        hover_color=BLUE_HOVER,
        command=apply_theme
    ).pack(
        anchor="w",
        padx=20,
        pady=(0, 20)
    )

    # ==========================================
    # Database
    # ==========================================

    database = ctk.CTkFrame(
        settings_frame,
        fg_color=CARD,
        border_width=1,
        border_color=BORDER,
        corner_radius=12
    )

    database.grid(
        row=0,
        column=1,
        sticky="nsew",
        padx=(7, 15),
        pady=5
    )

    ctk.CTkLabel(
        database,
        text="🗄 Database",
        font=("Segoe UI", 20, "bold"),
        text_color=TEXT
    ).pack(
        anchor="w",
        padx=20,
        pady=(20, 15)
    )

    ctk.CTkLabel(
        database,
        text="Status : Connected",
        font=("Segoe UI", 13),
        text_color=GREEN
    ).pack(
        anchor="w",
        padx=20
    )

    ctk.CTkLabel(
        database,
        text="Create a backup copy of the current database.",
        font=("Segoe UI", 13),
        text_color=TEXT2
    ).pack(
        anchor="w",
        padx=20,
        pady=(8, 0)
    )

    def guarded_backup():

        if not db.has_permission(current_user, "backup.create"):
            messagebox.showwarning(
                "Backup", "You don't have permission to create backups."
            )
            return

        backup_database()

    ctk.CTkButton(
        database,
        text="Backup Database",
        width=170,
        height=38,
        fg_color=BLUE,
        hover_color=BLUE_HOVER,
        state="normal" if db.has_permission(current_user, "backup.create") else "disabled",
        command=guarded_backup
    ).pack(
        anchor="w",
        padx=20,
        pady=(20, 8)
    )

    def guarded_restore():
        if not db.has_permission(current_user, "backup.restore"):
            messagebox.showwarning("Restore", "You don't have permission to restore backups.")
            return
        restore_database_from_file()

    ctk.CTkButton(
        database,
        text="Restore Database Backup",
        width=210,
        height=38,
        fg_color=RED,
        hover_color=RED,
        state="normal" if db.has_permission(current_user, "backup.restore") else "disabled",
        command=guarded_restore,
    ).pack(anchor="w", padx=20, pady=(0, 20))

    # ==========================================
    # Company
    # ==========================================

    company = ctk.CTkFrame(
        settings_frame,
        fg_color=CARD,
        border_width=1,
        border_color=BORDER,
        corner_radius=12
    )

    company.grid(
        row=1,
        column=0,
        sticky="nsew",
        padx=(15, 7),
        pady=5
    )

    ctk.CTkLabel(
        company,
        text="🏢 Company",
        font=("Segoe UI", 20, "bold"),
        text_color=TEXT
    ).pack(
        anchor="w",
        padx=20,
        pady=(20, 15)
    )

    company_name = ctk.CTkEntry(
        company,
        width=250,
        placeholder_text="Company Name"
    )

    company_name.pack(
        anchor="w",
        padx=20,
        pady=5
    )

    company_address = ctk.CTkEntry(
        company,
        width=250,
        placeholder_text="Company Address"
    )

    company_address.pack(
        anchor="w",
        padx=20,
        pady=5
    )

    phone_number = ctk.CTkEntry(
        company,
        width=250,
        placeholder_text="Phone Number"
    )

    phone_number.pack(
        anchor="w",
        padx=20,
        pady=5
    )

    contact_name = ctk.CTkEntry(
        company,
        width=250,
        placeholder_text="Contact Name"
    )

    contact_name.pack(
        anchor="w",
        padx=20,
        pady=(5, 20)
    )

    # ==========================================
    # About
    # ==========================================

    about = ctk.CTkFrame(
        settings_frame,
        fg_color=CARD,
        border_width=1,
        border_color=BORDER,
        corner_radius=12
    )

    about.grid(
        row=1,
        column=1,
        sticky="nsew",
        padx=(7, 15),
        pady=5
    )

    ctk.CTkLabel(
        about,
        text="ℹ About",
        font=("Segoe UI", 20, "bold"),
        text_color=TEXT
    ).pack(
        anchor="w",
        padx=20,
        pady=(20, 15)
    )

    ctk.CTkLabel(
        about,
        text="ERP Project Management",
        font=("Segoe UI", 18, "bold"),
        text_color=TEXT
    ).pack(
        anchor="w",
        padx=20
    )

    ctk.CTkLabel(
        about,
        text="Version : 1.0.0",
        font=("Segoe UI", 13),
        text_color=TEXT2
    ).pack(
        anchor="w",
        padx=20,
        pady=5
    )

    ctk.CTkLabel(
        about,
        text="Developer : Sahand Saadat",
        font=("Segoe UI", 13),
        text_color=TEXT2
    ).pack(
        anchor="w",
        padx=20
    )

    ctk.CTkButton(
        about,
        text="Check for Updates",
        width=180,
        height=38,
        fg_color=VIEW,
        hover_color=VIEW_HOVER
    ).pack(
        anchor="w",
        padx=20,
        pady=20
    )

    # ==========================================
    # Archive
    # ==========================================

    archive = ctk.CTkFrame(
        settings_frame,
        fg_color=CARD,
        border_width=1,
        border_color=BORDER,
        corner_radius=12
    )

    archive.grid(
        row=2,
        column=0,
        columnspan=2,
        sticky="nsew",
        padx=15,
        pady=(5, 15)
    )

    ctk.CTkLabel(
        archive,
        text="🗃 Archive",
        font=("Segoe UI", 20, "bold"),
        text_color=TEXT
    ).pack(
        anchor="w",
        padx=20,
        pady=(20, 10)
    )

    ctk.CTkLabel(
        archive,
        text="View, restore or permanently delete archived items.",
        font=("Segoe UI", 13),
        text_color=TEXT2
    ).pack(
        anchor="w",
        padx=20
    )

    def open_archive():

        if not db.has_permission(current_user, "archive.view"):
            messagebox.showwarning(
                "Archive", "You don't have permission to view the Archive."
            )
            return

        create_archive(
            parent,
            current_user
        )

    ctk.CTkButton(
        archive,
        text="Open Archive",
        width=160,
        height=38,
        state="normal" if db.has_permission(current_user, "archive.view") else "disabled",
        command=open_archive
    ).pack(
        anchor="w",
        padx=20,
        pady=20
    )

    # ==========================================
    # Lists  +  History
    # ==========================================

    def make_section(row, title, text, button_text, command):

        section = ctk.CTkFrame(
            settings_frame,
            fg_color=CARD,
            border_width=1,
            border_color=BORDER,
            corner_radius=12
        )

        section.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="nsew",
            padx=15,
            pady=(5, 15)
        )

        ctk.CTkLabel(
            section,
            text=title,
            font=("Segoe UI", 20, "bold"),
            text_color=TEXT
        ).pack(anchor="w", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            section,
            text=text,
            font=("Segoe UI", 13),
            text_color=TEXT2
        ).pack(anchor="w", padx=20)

        ctk.CTkButton(
            section,
            text=button_text,
            width=160,
            height=38,
            command=command
        ).pack(anchor="w", padx=20, pady=20)

    def open_lists():

        if not db.has_permission(current_user, "settings.manage"):
            messagebox.showwarning(
                "Lists", "You don't have permission to manage Lists."
            )
            return

        create_lists(parent, current_user)

    def open_history():

        if not db.has_permission(current_user, "history.view"):
            messagebox.showwarning(
                "History", "You don't have permission to view History."
            )
            return

        create_history(parent, current_user)

    make_section(
        3,
        "🗂 Lists",
        "Add or edit statuses, priorities, categories, clients, managers, "
        "departments and phases.",
        "Manage Lists",
        open_lists
    )

    make_section(
        4,
        "🕘 History",
        "Every add, edit, delete and restore. Clear it any time.",
        "Open History",
        open_history
    )

    def make_roles_section():

        from .roles import create_roles

        def open_roles():

            if not db.has_permission(current_user, "roles.manage"):
                messagebox.showwarning(
                    "Roles", "You don't have permission to manage roles."
                )
                return

            create_roles(parent, current_user)

        make_section(
            5,
            "🛡 Roles & Permissions",
            "Create roles and decide exactly what each one can do.",
            "Manage Roles",
            open_roles
        )

    make_roles_section()
