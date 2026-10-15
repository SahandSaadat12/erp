"""
Settings -> History

Every add / edit / delete / restore is listed here.  "Clear History"
empties the log (the real data is never touched).
"""

import customtkinter as ctk
from tkinter import ttk, messagebox

from config import *
import database as db


ACTIONS = ["All", "Add", "Edit", "Delete", "Restore", "Purge"]

ACTION_COLORS = {
    "add": GREEN,
    "edit": ORANGE,
    "delete": RED,
    "restore": BLUE,
    "purge": RED,
}

ACTION_ICONS = {
    "add": "＋ Added",
    "edit": "✎ Edited",
    "delete": "🗑 Deleted",
    "restore": "↩ Restored",
    "purge": "✖ Deleted forever",
}


def show_details(parent, row):

    _id, ts, action, entity, entity_id, label, old_json, new_json, performed_by = row

    window = ctk.CTkToplevel(parent)
    window.title("History details")
    window.geometry("760x520")
    window.transient(parent)
    window.after(120, lambda: (window.grab_set(), window.focus_force()))

    window.grid_columnconfigure(0, weight=1)
    window.grid_rowconfigure(2, weight=1)

    ctk.CTkLabel(
        window,
        text=f"{ACTION_ICONS.get(action, action)}  ·  "
             f"{db.ENTITY_TITLES.get(entity, entity)}",
        font=("Segoe UI", 20, "bold"), text_color=TEXT
    ).grid(row=0, column=0, sticky="w", padx=20, pady=(16, 2))

    ctk.CTkLabel(
        window, text=f"{label}\n{ts}" + (f"  ·  by {performed_by}" if performed_by else ""),
        justify="left", font=FONT_NORMAL, text_color=TEXT2
    ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 10))

    changes = db.describe_changes(old_json, new_json)

    two_sided = bool(old_json) and bool(new_json)

    table = ttk.Treeview(window, show="headings")
    table.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 10))

    if two_sided:
        table["columns"] = ("field", "before", "after")
        table.heading("field", text="Field")
        table.heading("before", text="Before")
        table.heading("after", text="After")
        table.column("field", width=170)
        table.column("before", width=260)
        table.column("after", width=260)

        for field, before, after in changes:
            table.insert("", "end", values=(field, before, after))

    else:
        table["columns"] = ("field", "value")
        table.heading("field", text="Field")
        table.heading("value", text="Value")
        table.column("field", width=190)
        table.column("value", width=520)

        for field, before, after in changes:
            table.insert("", "end", values=(field, after or before))

    if not changes:
        table.insert("", "end", values=("(no field changes recorded)", "", ""))

    ctk.CTkButton(
        window, text="Close", width=110, height=38,
        fg_color=NEUTRAL, hover_color=NEUTRAL_HOVER, command=window.destroy
    ).grid(row=3, column=0, sticky="e", padx=20, pady=(0, 16))


def create_history(parent, current_user=None):

    from .settings import create_settings        # avoid circular import

    for widget in parent.winfo_children():
        widget.destroy()

    for _row in range(8):
        parent.grid_rowconfigure(_row, weight=0)

    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(2, weight=1)

    # ---------------- header ----------------
    header = ctk.CTkFrame(parent, fg_color="transparent")
    header.grid(row=0, column=0, sticky="ew", padx=20, pady=(10, 5))
    header.grid_columnconfigure(1, weight=1)

    ctk.CTkButton(
        header, text="← Back", width=90, height=36,
        fg_color=NEUTRAL, hover_color=NEUTRAL_HOVER,
        command=lambda: create_settings(parent, current_user)
    ).grid(row=0, column=0, padx=(0, 15))

    ctk.CTkLabel(
        header, text="🕘 History", font=("Segoe UI", 26, "bold"), text_color=TEXT
    ).grid(row=0, column=1, sticky="w")

    count_label = ctk.CTkLabel(
        header, text="", font=FONT_NORMAL, text_color=TEXT2
    )
    count_label.grid(row=0, column=2, sticky="e")

    # ---------------- filters ----------------
    filters = ctk.CTkFrame(parent, fg_color="transparent")
    filters.grid(row=1, column=0, sticky="ew", padx=20, pady=(5, 8))

    search = ctk.CTkEntry(
        filters, width=230, height=36, placeholder_text="Search name..."
    )
    search.pack(side="left", padx=(0, 8))

    action_box = ctk.CTkComboBox(
        filters, values=ACTIONS, width=130, height=36, state="readonly"
    )
    action_box.set("All")
    action_box.pack(side="left", padx=(0, 8))

    entity_box = ctk.CTkComboBox(
        filters, values=["All"] + list(db.ENTITY_TITLES.values()),
        width=170, height=36, state="readonly"
    )
    entity_box.set("All")
    entity_box.pack(side="left", padx=(0, 8))

    # ---------------- table ----------------
    body = ctk.CTkFrame(parent, fg_color="transparent")
    body.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 10))
    body.grid_columnconfigure(0, weight=1)
    body.grid_rowconfigure(0, weight=1)

    tree = ttk.Treeview(
        body, columns=("time", "action", "type", "name", "by"),
        show="headings", selectmode="browse"
    )
    tree.grid(row=0, column=0, sticky="nsew")

    for column, text, width in (
        ("time", "Time", 150), ("action", "Action", 130),
        ("type", "Type", 130), ("name", "Name", 260), ("by", "By", 120)
    ):
        tree.heading(column, text=text, anchor="w")
        tree.column(column, width=width, anchor="w")

    scroll = ttk.Scrollbar(body, orient="vertical", command=tree.yview)
    scroll.grid(row=0, column=1, sticky="ns")
    tree.configure(yscrollcommand=scroll.set)

    for action, color in ACTION_COLORS.items():
        tree.tag_configure(action, foreground=color)

    rows = {}

    def load(*_):

        rows.clear()

        for item in tree.get_children():
            tree.delete(item)

        data = db.get_history(
            search=search.get().strip(),
            action=action_box.get(),
            entity=entity_box.get()
        )

        for row in data:
            rows[str(row[0])] = row

            tree.insert("", "end", iid=str(row[0]), tags=(row[2],), values=(
                row[1], ACTION_ICONS.get(row[2], row[2]),
                db.ENTITY_TITLES.get(row[3], row[3]), row[5] or "", row[8] or "-"
            ))

        total = db.get_history_count()

        count_label.configure(
            text=f"{len(data)} shown · {total} total" if len(data) != total
            else f"{total} record(s)"
        )

    def open_details(*_):

        selection = tree.selection()

        if not selection:
            messagebox.showwarning("History", "Please select a record first.")
            return

        show_details(parent, rows[selection[0]])

    def clear():

        if not db.has_permission(current_user, "history.clear"):
            messagebox.showwarning(
                "History", "You don't have permission to clear History."
            )
            return

        total = db.get_history_count()

        if not total:
            messagebox.showinfo("History", "The history is already empty.")
            return

        if messagebox.askyesno(
            "Clear History",
            f"Delete all {total} history records?\n\n"
            "Your projects, contracts and other data are NOT affected, "
            "only this log. This can't be undone."
        ):
            db.clear_history()
            load()

    ctk.CTkButton(
        filters, text="⟳ Refresh", width=110, height=36,
        fg_color=VIEW, hover_color=VIEW_HOVER, command=load
    ).pack(side="left", padx=(0, 8))

    ctk.CTkButton(
        filters, text="Details", width=100, height=36,
        fg_color=BLUE, hover_color=BLUE_HOVER, command=open_details
    ).pack(side="left", padx=(0, 8))

    ctk.CTkButton(
        filters, text="🧹 Clear History", width=150, height=36,
        fg_color=DELETE, hover_color=DELETE_HOVER, command=clear,
        state="normal" if db.has_permission(current_user, "history.clear") else "disabled"
    ).pack(side="right")

    search.bind("<Return>", load)
    action_box.configure(command=load)
    entity_box.configure(command=load)
    tree.bind("<Double-1>", open_details)

    load()
