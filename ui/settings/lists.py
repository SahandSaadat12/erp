"""
Settings -> Lists

Add / rename / hide / reorder / delete the values that appear in the
drop-downs (project status, priority, expense category ...) and manage
clients, managers, departments and phases.
"""

import customtkinter as ctk
from tkinter import ttk, messagebox

from config import *
import database as db


# ----------------------------------------------------------------------
# small form for entities
# ----------------------------------------------------------------------

class FormDialog(ctk.CTkToplevel):

    def __init__(self, parent, title, fields, initial=None):

        super().__init__(parent)

        self.title(title)
        self.geometry("460x%d" % (150 + 78 * len(fields)))
        self.resizable(False, False)
        self.transient(parent)
        self.result = None

        self.entries = {}
        initial = initial or {}

        for column, label, required in fields:

            ctk.CTkLabel(
                self,
                text=label + (" *" if required else ""),
                font=FONT_NORMAL,
                text_color=TEXT
            ).pack(anchor="w", padx=22, pady=(14, 2))

            entry = ctk.CTkEntry(self, height=36)
            entry.pack(fill="x", padx=22)

            value = initial.get(column)

            if value is not None:
                entry.insert(0, str(value))

            self.entries[column] = entry

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(side="bottom", fill="x", padx=22, pady=18)

        ctk.CTkButton(
            buttons, text="Save", width=120, height=38,
            fg_color=BLUE, hover_color=BLUE_HOVER, command=self._save
        ).pack(side="right")

        ctk.CTkButton(
            buttons, text="Cancel", width=110, height=38,
            fg_color=NEUTRAL, hover_color=NEUTRAL_HOVER, command=self.destroy
        ).pack(side="right", padx=(0, 10))

        self.after(120, self._take_focus)

    def _take_focus(self):
        try:
            self.grab_set()
            self.focus_force()
        except Exception:
            pass

    def _save(self):
        self.result = {c: e.get() for c, e in self.entries.items()}
        self.destroy()


def ask_form(parent, title, fields, initial=None):
    dialog = FormDialog(parent, title, fields, initial)
    dialog.wait_window()
    return dialog.result


# ----------------------------------------------------------------------
# page
# ----------------------------------------------------------------------

def create_lists(parent, current_user=None):

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
        header, text="🗂 Lists", font=("Segoe UI", 26, "bold"), text_color=TEXT
    ).grid(row=0, column=1, sticky="w")

    # ---------------- selector ----------------
    sources = {}

    for key, (title, *_rest) in db.CATEGORIES.items():
        sources[title] = ("lookup", key)

    for key, (title, *_rest) in db.ENTITIES.items():
        sources[title] = ("entity", key)

    selector_row = ctk.CTkFrame(parent, fg_color="transparent")
    selector_row.grid(row=1, column=0, sticky="ew", padx=20, pady=(5, 8))

    ctk.CTkLabel(
        selector_row, text="List:", font=FONT_NORMAL, text_color=TEXT2
    ).pack(side="left", padx=(0, 10))

    selector = ctk.CTkComboBox(
        selector_row, values=list(sources), width=280, height=36,
        state="readonly", font=FONT_NORMAL
    )
    selector.pack(side="left")
    selector.set(list(sources)[0])

    hint = ctk.CTkLabel(
        selector_row, text="", font=("Segoe UI", 12), text_color=TEXT2
    )
    hint.pack(side="left", padx=18)

    # ---------------- table ----------------
    body = ctk.CTkFrame(parent, fg_color="transparent")
    body.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 10))
    body.grid_columnconfigure(0, weight=1)
    body.grid_rowconfigure(0, weight=1)

    tree = ttk.Treeview(body, show="headings", selectmode="browse")
    tree.grid(row=0, column=0, sticky="nsew")

    scroll = ttk.Scrollbar(body, orient="vertical", command=tree.yview)
    scroll.grid(row=0, column=1, sticky="ns")
    tree.configure(yscrollcommand=scroll.set)

    # ---------------- buttons ----------------
    bar = ctk.CTkFrame(parent, fg_color="transparent")
    bar.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 15))

    def make(text, color, hover, width=110):
        button = ctk.CTkButton(
            bar, text=text, width=width, height=38,
            fg_color=color, hover_color=hover
        )
        button.pack(side="left", padx=(0, 8))
        return button

    add_btn = make("＋ Add", GREEN, GREEN_HOVER)
    edit_btn = make("✎ Edit / Rename", BLUE, BLUE_HOVER, 150)
    vis_btn = make("👁 Hide / Show", VIEW, VIEW_HOVER, 140)
    up_btn = make("▲", NEUTRAL, NEUTRAL_HOVER, 50)
    down_btn = make("▼", NEUTRAL, NEUTRAL_HOVER, 50)
    del_btn = make("🗑 Delete", DELETE, DELETE_HOVER)

    # ---------------- state ----------------
    state = {"kind": None, "key": None}

    def selected_id():
        selection = tree.selection()
        return int(selection[0]) if selection else None

    def set_columns(columns):
        tree["columns"] = [c for c, _, _ in columns]

        for column, label, width in columns:
            tree.heading(column, text=label, anchor="w")
            tree.column(column, width=width, anchor="w", stretch=True)

    def load(select_id=None):

        kind, key = sources[selector.get()]
        state["kind"], state["key"] = kind, key

        for item in tree.get_children():
            tree.delete(item)

        lookup_only = kind == "lookup"

        for button in (vis_btn, up_btn, down_btn):
            button.configure(state="normal" if lookup_only else "disabled")

        if kind == "lookup":

            title, usage, defaults, system = db.CATEGORIES[key]

            hint.configure(
                text="Values with a lock are used by the program logic: "
                     "they can't be renamed or deleted, but you can add new ones."
            )

            set_columns([
                ("value", "Value", 300), ("used", "Used by", 100),
                ("kind", "Kind", 110), ("visible", "Visible in forms", 140),
            ])

            for row_id, value, order, is_system, is_active in db.get_lookup_rows(key):
                tree.insert("", "end", iid=str(row_id), values=(
                    ("🔒 " if is_system else "") + value,
                    f"{db.usage_count(key, value)} record(s)",
                    "System" if is_system else "Custom",
                    "Yes" if is_active else "Hidden",
                ))

        else:

            title, table, display, fields = db.ENTITIES[key]

            hint.configure(
                text="Deleting moves the item to the Archive (it can be restored)."
            )

            set_columns([(c, label, 150) for c, label, _ in fields])

            for row in db.get_entity_rows(key):
                tree.insert("", "end", iid=str(row[0]), values=[
                    "" if v is None else v for v in row[1:]
                ])

        if select_id is not None and tree.exists(str(select_id)):
            tree.selection_set(str(select_id))
            tree.see(str(select_id))

    def need_selection():
        row_id = selected_id()

        if row_id is None:
            messagebox.showwarning("Lists", "Please select an item first.")

        return row_id

    def guard(function):
        try:
            return function()
        except ValueError as error:
            messagebox.showerror("Lists", str(error))
        except Exception as error:
            messagebox.showerror("Lists", f"Unexpected error:\n\n{error}")

    # ---------------- actions ----------------
    def add_item():

        if state["kind"] == "lookup":

            dialog = ctk.CTkInputDialog(text="New value:", title="Add")
            value = dialog.get_input()

            if value:
                guard(lambda: db.add_value(state["key"], value))
                load()

        else:

            title, table, display, fields = db.ENTITIES[state["key"]]

            values = ask_form(parent, f"Add - {title}", fields)

            if values is not None:
                guard(lambda: db.save_entity(state["key"], None, values, current_user=current_user))
                load()

    def edit_item():

        row_id = need_selection()

        if row_id is None:
            return

        if state["kind"] == "lookup":

            rows = {r[0]: r for r in db.get_lookup_rows(state["key"])}
            _, old, _, is_system, _ = rows[row_id]

            if is_system:
                messagebox.showinfo(
                    "Lists",
                    f"'{old}' is used by the program logic and can't be renamed."
                )
                return

            dialog = ctk.CTkInputDialog(text=f"Rename '{old}' to:", title="Rename")
            value = dialog.get_input()

            if not value or value.strip() == old:
                return

            used = db.usage_count(state["key"], old)

            if used and not messagebox.askyesno(
                "Rename",
                f"{used} record(s) use '{old}'.\n\n"
                f"They will all be changed to '{value.strip()}'. Continue?"
            ):
                return

            guard(lambda: db.rename_value(row_id, value))
            load(row_id)

        else:

            title, table, display, fields = db.ENTITIES[state["key"]]

            # read from the database (the tree may turn "0912..." into 912)
            record = next(
                (r for r in db.get_entity_rows(state["key"]) if r[0] == row_id),
                None
            )

            current = dict(zip(
                [c for c, _, _ in fields],
                list(record[1:]) if record else []
            ))

            values = ask_form(parent, f"Edit - {title}", fields, current)

            if values is not None:
                guard(lambda: db.save_entity(state["key"], row_id, values, current_user=current_user))
                load(row_id)

    def toggle_visible():

        row_id = need_selection()

        if row_id is None:
            return

        rows = {r[0]: r for r in db.get_lookup_rows(state["key"])}

        guard(lambda: db.set_active(row_id, not rows[row_id][4]))
        load(row_id)

    def move(direction):

        row_id = selected_id()

        if row_id is None:
            return

        db.move_value(row_id, direction)
        load(row_id)

    def delete_item():

        row_id = need_selection()

        if row_id is None:
            return

        if state["kind"] == "lookup":

            if messagebox.askyesno("Delete", "Delete this value?"):
                guard(lambda: db.delete_value(row_id))
                load()

        else:

            title, table, display, fields = db.ENTITIES[state["key"]]
            used = db.entity_usage(state["key"], row_id)

            note = (
                f"\n\n{used} record(s) reference it and will lose that link."
                if used else ""
            )

            if messagebox.askyesno(
                "Delete",
                "Move this item to the Archive?\n"
                "You can restore it from Settings -> Archive." + note
            ):
                guard(lambda: db.archive_cascade(table, row_id))
                load()

    add_btn.configure(command=add_item)
    edit_btn.configure(command=edit_item)
    vis_btn.configure(command=toggle_visible)
    up_btn.configure(command=lambda: move(-1))
    down_btn.configure(command=lambda: move(1))
    del_btn.configure(command=delete_item)

    selector.configure(command=lambda _value: load())
    tree.bind("<Double-1>", lambda _event: edit_item())

    load()
