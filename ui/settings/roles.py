"""
Settings -> Roles & Permissions

Create roles, rename/delete custom ones, and pick exactly which
permissions each role grants. The built-in "Manager" role always keeps
every permission (see db/permissions.py) so the app can never lock
itself out of its own Settings/Roles screen.
"""

import customtkinter as ctk
from tkinter import messagebox

from config import *
import database as db


def create_roles(parent, current_user=None):

    from .settings import create_settings

    for widget in parent.winfo_children():
        widget.destroy()

    parent.grid_columnconfigure(1, weight=1)
    parent.grid_rowconfigure(1, weight=1)

    # ---------------- header ----------------
    header = ctk.CTkFrame(parent, fg_color="transparent")
    header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(10, 5))
    header.grid_columnconfigure(1, weight=1)

    ctk.CTkButton(
        header, text="← Back", width=90, height=36,
        fg_color=NEUTRAL, hover_color=NEUTRAL_HOVER,
        command=lambda: create_settings(parent, current_user)
    ).grid(row=0, column=0, padx=(0, 15))

    ctk.CTkLabel(
        header, text="🛡 Roles & Permissions",
        font=("Segoe UI", 26, "bold"), text_color=TEXT
    ).grid(row=0, column=1, sticky="w")

    # ---------------- role list (left) ----------------
    left = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=12,
                         border_width=1, border_color=BORDER)
    left.grid(row=1, column=0, sticky="nsw", padx=(20, 10), pady=(0, 15))

    role_list = ctk.CTkScrollableFrame(left, width=220, fg_color="transparent")
    role_list.pack(fill="both", expand=True, padx=10, pady=10)

    role_buttons_bar = ctk.CTkFrame(left, fg_color="transparent")
    role_buttons_bar.pack(fill="x", padx=10, pady=(0, 10))

    ctk.CTkButton(
        role_buttons_bar, text="＋ New Role", height=34,
        fg_color=GREEN, hover_color=GREEN_HOVER,
        command=lambda: add_role()
    ).pack(fill="x", pady=(0, 6))

    rename_btn = ctk.CTkButton(role_buttons_bar, text="✎ Rename", height=34)
    rename_btn.pack(fill="x", pady=(0, 6))

    delete_btn = ctk.CTkButton(
        role_buttons_bar, text="🗑 Delete", height=34,
        fg_color=DELETE, hover_color=DELETE_HOVER
    )
    delete_btn.pack(fill="x")

    # ---------------- permission matrix (right) ----------------
    right = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=12,
                          border_width=1, border_color=BORDER)
    right.grid(row=1, column=1, sticky="nsew", padx=(10, 20), pady=(0, 15))
    right.grid_rowconfigure(1, weight=1)
    right.grid_columnconfigure(0, weight=1)

    role_title = ctk.CTkLabel(
        right, text="Select a role", font=("Segoe UI", 20, "bold"), text_color=TEXT
    )
    role_title.grid(row=0, column=0, sticky="w", padx=20, pady=(18, 4))

    perm_area = ctk.CTkScrollableFrame(right, fg_color="transparent")
    perm_area.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

    save_bar = ctk.CTkFrame(right, fg_color="transparent")
    save_bar.grid(row=2, column=0, sticky="e", padx=20, pady=(0, 18))

    save_btn = ctk.CTkButton(
        save_bar, text="Save Permissions", width=180, height=40,
        fg_color=BLUE, hover_color=BLUE_HOVER
    )
    save_btn.pack(side="right")

    state = {"role_id": None, "role_name": None, "is_system": False, "checks": {}}

    can_manage = db.has_permission(current_user, "roles.manage")

    def refresh_roles(select_id=None):

        for widget in role_list.winfo_children():
            widget.destroy()

        roles = db.list_roles()

        for role_id, name, is_system in roles:

            count = db.role_user_count(name)

            button = ctk.CTkButton(
                role_list,
                text=f"{'🔒 ' if is_system else ''}{name}  ({count})",
                anchor="w", height=36,
                fg_color=BLUE if role_id == state["role_id"] else "transparent",
                hover_color=CARD_HOVER,
                text_color=TEXT,
                command=lambda r=role_id, n=name, s=is_system: select_role(r, n, bool(s))
            )
            button.pack(fill="x", pady=2)

        if select_id is not None:
            match = next((r for r in roles if r[0] == select_id), None)
            if match:
                select_role(match[0], match[1], bool(match[2]))
        elif roles and state["role_id"] is None:
            select_role(roles[0][0], roles[0][1], bool(roles[0][2]))

    def select_role(role_id, name, is_system):

        state["role_id"] = role_id
        state["role_name"] = name
        state["is_system"] = is_system
        state["checks"] = {}

        role_title.configure(
            text=f"{name}" + ("  🔒 built-in (always full access)" if is_system else "")
        )

        for widget in perm_area.winfo_children():
            widget.destroy()

        granted = db.get_permissions_for_role(name)

        editable = can_manage and not is_system

        for group_title, items in db.PERMISSIONS.items():

            ctk.CTkLabel(
                perm_area, text=group_title, font=("Segoe UI", 15, "bold"),
                text_color=TEXT
            ).pack(anchor="w", pady=(10, 2))

            row = ctk.CTkFrame(perm_area, fg_color="transparent")
            row.pack(fill="x", padx=(10, 0))

            for key, label in items:

                var = ctk.BooleanVar(
                    value=is_system or (key in granted)
                )

                checkbox = ctk.CTkCheckBox(
                    row, text=label, variable=var,
                    state="normal" if editable else "disabled"
                )
                checkbox.pack(side="left", padx=(0, 18), pady=4)

                state["checks"][key] = var

        refresh_roles_buttons()

    def refresh_roles_buttons():

        editable = can_manage and not state["is_system"] and state["role_id"] is not None

        rename_btn.configure(
            state="normal" if (can_manage and state["role_id"] and not state["is_system"]) else "disabled",
            command=lambda: rename_role()
        )
        delete_btn.configure(
            state="normal" if (can_manage and state["role_id"] and not state["is_system"]) else "disabled",
            command=lambda: delete_role()
        )
        save_btn.configure(state="normal" if editable else "disabled")

    def guard():
        if not can_manage:
            messagebox.showwarning(
                "Roles", "You don't have permission to manage roles."
            )
            return False
        return True

    def add_role():

        if not guard():
            return

        dialog = ctk.CTkInputDialog(text="New role name:", title="New Role")
        name = dialog.get_input()

        if not name:
            return

        try:
            db.create_role(name)
        except ValueError as error:
            messagebox.showerror("Roles", str(error))
            return

        refresh_roles()

    def rename_role():

        if not guard() or state["role_id"] is None:
            return

        dialog = ctk.CTkInputDialog(
            text=f"Rename '{state['role_name']}' to:", title="Rename Role"
        )
        name = dialog.get_input()

        if not name:
            return

        try:
            db.rename_role(state["role_id"], name)
        except ValueError as error:
            messagebox.showerror("Roles", str(error))
            return

        refresh_roles(select_id=state["role_id"])

    def delete_role():

        if not guard() or state["role_id"] is None:
            return

        count = db.role_user_count(state["role_name"])

        if count:
            messagebox.showerror(
                "Roles",
                f"'{state['role_name']}' is assigned to {count} user(s). "
                "Reassign them to another role first."
            )
            return

        if not messagebox.askyesno(
            "Delete Role", f"Delete the role '{state['role_name']}'?"
        ):
            return

        try:
            db.delete_role(state["role_id"])
        except ValueError as error:
            messagebox.showerror("Roles", str(error))
            return

        state["role_id"] = None
        refresh_roles()

    def save_permissions():

        if not guard() or state["role_id"] is None:
            return

        selected = [key for key, var in state["checks"].items() if var.get()]

        try:
            db.set_role_permissions(state["role_id"], selected)
        except ValueError as error:
            messagebox.showerror("Roles", str(error))
            return

        messagebox.showinfo(
            "Roles",
            f"Permissions saved for '{state['role_name']}'.\n\n"
            "Users with this role will see the change next time they sign in."
        )

    save_btn.configure(command=save_permissions)

    refresh_roles()
