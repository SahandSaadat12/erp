import json

import customtkinter as ctk
from tkinter import ttk, messagebox

from config import *
from database import (
    get_archived_records,
    get_archive_event,
    restore_archive_event,
    permanently_delete_archive_event,
    has_permission,
)


def create_archive(parent, current_user=None):

    for widget in parent.winfo_children():
        widget.destroy()

    parent.grid_columnconfigure(0, weight=1)

    parent.grid_rowconfigure(0, weight=0)
    parent.grid_rowconfigure(1, weight=0)
    parent.grid_rowconfigure(2, weight=0)
    parent.grid_rowconfigure(3, weight=1)
    parent.grid_rowconfigure(4, weight=0)

    # =====================================================
    # Header
    # =====================================================

    header = ctk.CTkFrame(
        parent,
        fg_color="transparent"
    )

    header.grid(
        row=0,
        column=0,
        sticky="ew",
        padx=20,
        pady=(10, 15)
    )

    header.grid_columnconfigure(
        0,
        weight=1
    )

    title = ctk.CTkLabel(
        header,
        text="🗃 Archive",
        font=("Segoe UI", 28, "bold"),
        text_color=TEXT
    )

    title.grid(
        row=0,
        column=0,
        sticky="w"
    )

    subtitle = ctk.CTkLabel(
        header,
        text=(
            "Deleted items can be restored "
            "or permanently deleted."
        ),
        font=("Segoe UI", 13),
        text_color=TEXT2
    )

    subtitle.grid(
        row=1,
        column=0,
        sticky="w",
        pady=(4, 0)
    )

    # =====================================================
    # Filters
    # =====================================================

    filter_frame = ctk.CTkFrame(
        parent,
        fg_color=CARD,
        border_width=1,
        border_color=BORDER,
        corner_radius=12
    )

    filter_frame.grid(
        row=1,
        column=0,
        sticky="ew",
        padx=20,
        pady=(0, 10)
    )

    filter_frame.grid_columnconfigure(
        1,
        weight=1
    )

    search = ctk.CTkEntry(
        filter_frame,
        width=280,
        placeholder_text="🔍 Search..."
    )

    search.grid(
        row=0,
        column=0,
        padx=15,
        pady=15
    )

    type_filter = ctk.CTkComboBox(
        filter_frame,
        width=170,
        values=[
            "All Types",
            "Expense",
            "Project",
            "Client",
            "Task",
            "Contract",
            "Document",
            "Project Phase"
        ]
    )

    type_filter.set(
        "All Types"
    )

    type_filter.grid(
        row=0,
        column=1,
        padx=10,
        pady=15,
        sticky="w"
    )

    refresh_button = ctk.CTkButton(
        filter_frame,
        text="🔄 Refresh",
        width=120,
        fg_color=BLUE,
        hover_color=BLUE_HOVER
    )

    refresh_button.grid(
        row=0,
        column=2,
        padx=15,
        pady=15
    )

    # =====================================================
    # Actions
    # =====================================================

    action_frame = ctk.CTkFrame(
        parent,
        fg_color="transparent",
        height=50
    )

    action_frame.grid(
        row=2,
        column=0,
        sticky="ew",
        padx=20,
        pady=(0, 10)
    )

    action_frame.grid_propagate(
        False
    )

    restore_button = ctk.CTkButton(
        action_frame,
        text="↩ Restore",
        width=140,
        height=38,
        state="disabled"
    )

    restore_button.pack(
        side="left",
        padx=(0, 8)
    )

    view_button = ctk.CTkButton(
        action_frame,
        text="👁 View Event",
        width=150,
        height=38,
        fg_color=NEUTRAL,
        hover_color=NEUTRAL_HOVER,
        state="disabled"
    )

    view_button.pack(
        side="left",
        padx=(0, 8)
    )

    delete_permanent_button = ctk.CTkButton(
        action_frame,
        text="🗑 Delete Permanently",
        width=180,
        height=38,
        fg_color=DELETE,
        hover_color=DELETE_HOVER,
        state="disabled"
    )

    delete_permanent_button.pack(
        side="left"
    )

    # =====================================================
    # Table
    # =====================================================

    table_frame = ctk.CTkFrame(
        parent,
        fg_color=CARD,
        corner_radius=12,
        border_width=1,
        border_color=BORDER
    )

    table_frame.grid(
        row=3,
        column=0,
        sticky="nsew",
        padx=20
    )

    table_frame.grid_rowconfigure(
        0,
        weight=1
    )

    table_frame.grid_columnconfigure(
        0,
        weight=1
    )

    tree = ttk.Treeview(
        table_frame,
        show="headings",
        columns=(
            "ID",
            "Type",
            "Name",
            "Deleted At"
        )
    )

    columns = {
        "ID": 70,
        "Type": 140,
        "Name": 320,
        "Deleted At": 190
    }

    for column, width in columns.items():

        tree.heading(
            column,
            text=column
        )

        tree.column(
            column,
            width=width,
            anchor="center"
        )

    scrollbar = ttk.Scrollbar(
        table_frame,
        orient="vertical",
        command=tree.yview
    )

    tree.configure(
        yscrollcommand=scrollbar.set
    )

    tree.grid(
        row=0,
        column=0,
        sticky="nsew",
        padx=(12, 0),
        pady=12
    )

    scrollbar.grid(
        row=0,
        column=1,
        sticky="ns",
        padx=(0, 12),
        pady=12
    )

    # =====================================================
    # Footer
    # =====================================================

    footer = ctk.CTkFrame(
        parent,
        fg_color="transparent"
    )

    footer.grid(
        row=4,
        column=0,
        sticky="ew",
        padx=20,
        pady=(10, 15)
    )

    showing = ctk.CTkLabel(
        footer,
        text="Showing : 0 Items",
        font=("Segoe UI", 14),
        text_color=TEXT2
    )

    showing.pack(
        side="right"
    )

    # =====================================================
    # Cache
    # =====================================================

    archive_cache = {}

    # =====================================================
    # Record Name
    # =====================================================

    def get_record_name(
        source_table,
        data
    ):

        try:

            record_data = json.loads(
                data
            )

        except (
            json.JSONDecodeError,
            TypeError
        ):

            return f"{source_table} Record"

        name_fields = [
            "title",
            "name",
            "project_name",
            "contract_name",
            "company_name",
            "client_name",
            "task_name",
            "document_name",
            "file_name"
        ]

        for field in name_fields:

            value = record_data.get(
                field
            )

            if (
                value is not None
                and str(value).strip()
            ):

                return str(value)

        return (
            f"{source_table} "
            f"#{record_data.get('id', '')}"
        )

    # =====================================================
    # Display Type
    # =====================================================

    def get_display_type(
        source_table
    ):

        type_names = {
            "expenses": "Expense",
            "projects": "Project",
            "clients": "Client",
            "tasks": "Task",
            "contracts": "Contract",
            "documents": "Document",
            "project_phases": "Project Phase"
        }

        return type_names.get(
            source_table,
            source_table.replace(
                "_",
                " "
            ).title()
        )

    # =====================================================
    # Format Value
    # =====================================================

    def format_value(value):

        if value is None:
            return "NULL"

        if isinstance(
            value,
            (dict, list)
        ):

            return json.dumps(
                value,
                ensure_ascii=False,
                indent=2
            )

        return str(value)

    # =====================================================
    # Get Selected
    # =====================================================

    def get_selected_item():

        selected = tree.selection()

        if not selected:
            return None

        values = tree.item(
            selected[0],
            "values"
        )

        if not values:
            return None

        return values

    # =====================================================
    # Buttons
    # =====================================================

    def update_action_buttons(
        event=None
    ):

        selected = tree.selection()

        if selected:

            restore_button.configure(
                state="normal"
            )

            view_button.configure(
                state="normal"
            )

            delete_permanent_button.configure(
                state="normal"
            )

        else:

            restore_button.configure(
                state="disabled"
            )

            view_button.configure(
                state="disabled"
            )

            delete_permanent_button.configure(
                state="disabled"
            )

    # =====================================================
    # Load Archive
    # =====================================================

    def load_archive():

        for item in tree.get_children():
            tree.delete(item)

        archive_cache.clear()

        keyword = (
            search.get()
            .strip()
            .lower()
        )

        selected_type = (
            type_filter.get()
        )

        records = get_archived_records()

        count = 0

        for record in records:

            archive_id = record[0]
            source_table = record[1]
            source_id = record[2]
            data = record[3]
            deleted_at = record[4]
            archive_group_id = record[5]

            item_type = get_display_type(
                source_table
            )

            item_name = get_record_name(
                source_table,
                data
            )

            # -----------------------------------------
            # Type filter
            # -----------------------------------------

            if (
                selected_type != "All Types"
                and item_type != selected_type
            ):
                continue

            # -----------------------------------------
            # Search
            # -----------------------------------------

            if keyword:

                searchable = (
                    f"{item_type} "
                    f"{item_name} "
                    f"{source_id} "
                    f"{archive_group_id}"
                ).lower()

                if keyword not in searchable:
                    continue

            try:

                formatted_date = (
                    deleted_at
                    .replace("T", " ")
                    [:19]
                )

            except (
                AttributeError,
                TypeError
            ):

                formatted_date = str(
                    deleted_at
                )

            tree_item = tree.insert(
                "",
                "end",
                values=(
                    archive_id,
                    item_type,
                    item_name,
                    formatted_date
                )
            )

            archive_cache[
                str(archive_id)
            ] = record

            count += 1

        showing.configure(
            text=f"Showing : {count} Items"
        )

        update_action_buttons()

    # =====================================================
    # View Event
    # =====================================================

    def view_selected_event():

        values = get_selected_item()

        if not values:
            return

        archive_id = str(
            values[0]
        )

        selected_record = (
            archive_cache.get(
                archive_id
            )
        )

        if not selected_record:
            messagebox.showerror(
                "Error",
                "Archive record could not be found.",
                parent=parent
            )
            return

        archive_group_id = (
            selected_record[5]
        )

        event_records = (
            get_archive_event(
                archive_group_id
            )
        )

        if not event_records:

            messagebox.showerror(
                "Error",
                "Archive event could not be found.",
                parent=parent
            )

            return

        main_record = event_records[0]

        source_table = main_record[1]
        data_json = main_record[3]
        deleted_at = main_record[4]

        try:

            main_data = json.loads(
                data_json
            )

        except (
            json.JSONDecodeError,
            TypeError
        ):

            main_data = {}

        main_name = get_record_name(
            source_table,
            data_json
        )

        # =================================================
        # Window
        # =================================================

        window = ctk.CTkToplevel(
            parent
        )

        window.title(
            f"Archive Event — {main_name}"
        )

        window.geometry(
            "1050x750"
        )

        window.minsize(
            850,
            600
        )

        window.transient(
            parent
        )

        # =================================================
        # Container
        # =================================================

        container = ctk.CTkFrame(
            window,
            fg_color="transparent"
        )

        container.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20
        )

        title_label = ctk.CTkLabel(
            container,
            text=f"👁 {main_name}",
            font=("Segoe UI", 26, "bold"),
            text_color=TEXT
        )

        title_label.pack(
            anchor="w"
        )

        subtitle_label = ctk.CTkLabel(
            container,
            text=(
                f"Delete Event • "
                f"{len(event_records)} archived records"
            ),
            font=("Segoe UI", 13),
            text_color=TEXT2
        )

        subtitle_label.pack(
            anchor="w",
            pady=(3, 15)
        )

        scroll = ctk.CTkScrollableFrame(
            container,
            fg_color="transparent"
        )

        scroll.pack(
            fill="both",
            expand=True
        )

        # =================================================
        # Event Information
        # =================================================

        info_card = ctk.CTkFrame(
            scroll,
            fg_color=CARD,
            border_width=1,
            border_color=BORDER,
            corner_radius=12
        )

        info_card.pack(
            fill="x",
            pady=(0, 12)
        )

        info_title = ctk.CTkLabel(
            info_card,
            text="Archive Event",
            font=("Segoe UI", 18, "bold"),
            text_color=TEXT
        )

        info_title.pack(
            anchor="w",
            padx=18,
            pady=(15, 10)
        )

        event_info = [
            ("Event ID", archive_group_id),
            ("Deleted At", deleted_at),
            ("Records", len(event_records))
        ]

        for field_name, value in event_info:

            row = ctk.CTkFrame(
                info_card,
                fg_color="transparent"
            )

            row.pack(
                fill="x",
                padx=18,
                pady=4
            )

            row.grid_columnconfigure(
                1,
                weight=1
            )

            label = ctk.CTkLabel(
                row,
                text=field_name,
                font=("Segoe UI", 13, "bold"),
                text_color=TEXT2,
                width=130,
                anchor="w"
            )

            label.grid(
                row=0,
                column=0,
                sticky="w"
            )

            value_label = ctk.CTkLabel(
                row,
                text=str(value),
                font=("Segoe UI", 13),
                text_color=TEXT,
                anchor="w"
            )

            value_label.grid(
                row=0,
                column=1,
                sticky="w",
                padx=(15, 0)
            )

        # =================================================
        # Event Records
        # =================================================

        records_title = ctk.CTkLabel(
            scroll,
            text="Records In This Event",
            font=("Segoe UI", 20, "bold"),
            text_color=TEXT
        )

        records_title.pack(
            anchor="w",
            pady=(5, 10)
        )

        for index, record in enumerate(
            event_records,
            start=1
        ):

            archive_id = record[0]
            record_table = record[1]
            record_id = record[2]
            record_data_json = record[3]

            try:

                record_data = json.loads(
                    record_data_json
                )

            except (
                json.JSONDecodeError,
                TypeError
            ):

                record_data = {}

            record_name = get_record_name(
                record_table,
                record_data_json
            )

            # ---------------------------------------------
            # Record Card
            # ---------------------------------------------

            record_card = ctk.CTkFrame(
                scroll,
                fg_color=CARD,
                border_width=1,
                border_color=BORDER,
                corner_radius=12
            )

            record_card.pack(
                fill="x",
                pady=6
            )

            card_header = ctk.CTkFrame(
                record_card,
                fg_color="transparent"
            )

            card_header.pack(
                fill="x",
                padx=18,
                pady=(14, 8)
            )

            card_header.grid_columnconfigure(
                0,
                weight=1
            )

            record_title = ctk.CTkLabel(
                card_header,
                text=(
                    f"{index}. "
                    f"{get_display_type(record_table)}"
                ),
                font=("Segoe UI", 16, "bold"),
                text_color=TEXT
            )

            record_title.grid(
                row=0,
                column=0,
                sticky="w"
            )

            record_name_label = ctk.CTkLabel(
                card_header,
                text=record_name,
                font=("Segoe UI", 13),
                text_color=TEXT2
            )

            record_name_label.grid(
                row=1,
                column=0,
                sticky="w",
                pady=(2, 0)
            )

            # ---------------------------------------------
            # Basic Information
            # ---------------------------------------------

            basic_info = ctk.CTkLabel(
                record_card,
                text=(
                    f"Archive ID: {archive_id}    "
                    f"Original ID: {record_id}    "
                    f"Table: {record_table}"
                ),
                font=("Segoe UI", 11),
                text_color=TEXT2
            )

            basic_info.pack(
                anchor="w",
                padx=18,
                pady=(0, 10)
            )

            # ---------------------------------------------
            # Complete Data
            # ---------------------------------------------

            for field_name, value in (
                record_data.items()
            ):

                row = ctk.CTkFrame(
                    record_card,
                    fg_color="transparent"
                )

                row.pack(
                    fill="x",
                    padx=18,
                    pady=3
                )

                row.grid_columnconfigure(
                    1,
                    weight=1
                )

                field_label = ctk.CTkLabel(
                    row,
                    text=str(field_name),
                    font=("Segoe UI", 12, "bold"),
                    text_color=TEXT2,
                    width=160,
                    anchor="nw"
                )

                field_label.grid(
                    row=0,
                    column=0,
                    sticky="nw"
                )

                value_label = ctk.CTkLabel(
                    row,
                    text=format_value(value),
                    font=("Segoe UI", 12),
                    text_color=TEXT,
                    anchor="nw",
                    justify="left",
                    wraplength=700
                )

                value_label.grid(
                    row=0,
                    column=1,
                    sticky="nw",
                    padx=(15, 0)
                )

            ctk.CTkFrame(
                record_card,
                height=8,
                fg_color="transparent"
            ).pack()

        # =================================================
        # Close
        # =================================================

        close_button = ctk.CTkButton(
            container,
            text="Close",
            width=120,
            height=36,
            command=window.destroy
        )

        close_button.pack(
            anchor="e",
            pady=(10, 0)
        )

    # =====================================================
    # Restore
    # =====================================================

    def restore_selected():

        if not has_permission(current_user, "archive.restore"):
            messagebox.showwarning(
                "Restore", "You don't have permission to restore items.",
                parent=parent
            )
            return

        values = get_selected_item()

        if not values:
            return

        archive_id = str(
            values[0]
        )

        selected_record = (
            archive_cache.get(
                archive_id
            )
        )

        if not selected_record:
            return

        archive_group_id = (
            selected_record[5]
        )

        item_type = values[1]
        item_name = values[2]

        result = messagebox.askyesno(
            "Restore Event",
            (
                "Restore this delete event?\n\n"
                f"Main item : {item_name}\n"
                f"Type : {item_type}\n\n"
                "All records belonging to this "
                "delete event will be restored."
            ),
            parent=parent
        )

        if not result:
            return

        try:

            success = restore_archive_event(
                archive_group_id
            )

            if success:

                messagebox.showinfo(
                    "Restore",
                    (
                        "The archive event was "
                        "restored successfully."
                    ),
                    parent=parent
                )

                load_archive()

        except Exception as error:

            messagebox.showerror(
                "Restore Error",
                str(error),
                parent=parent
            )

    # =====================================================
    # Permanent Delete
    # =====================================================

    def delete_selected_permanently():

        if not has_permission(current_user, "archive.permanent_delete"):
            messagebox.showwarning(
                "Delete Permanently",
                "You don't have permission to permanently delete items.",
                parent=parent
            )
            return

        values = get_selected_item()

        if not values:
            return

        archive_id = str(
            values[0]
        )

        selected_record = (
            archive_cache.get(
                archive_id
            )
        )

        if not selected_record:
            return

        archive_group_id = (
            selected_record[5]
        )

        item_type = values[1]
        item_name = values[2]

        result = messagebox.askyesno(
            "Permanently Delete",
            (
                "Are you sure?\n\n"
                f"Item : {item_name}\n"
                f"Type : {item_type}\n\n"
                "The entire archive event will be "
                "permanently deleted.\n\n"
                "This action cannot be undone."
            ),
            parent=parent
        )

        if not result:
            return

        try:

            success = (
                permanently_delete_archive_event(
                    archive_group_id
                )
            )

            if success:

                messagebox.showinfo(
                    "Delete",
                    (
                        "The archive event was "
                        "permanently deleted."
                    ),
                    parent=parent
                )

                load_archive()

        except Exception as error:

            messagebox.showerror(
                "Delete Error",
                str(error),
                parent=parent
            )

    # =====================================================
    # Events
    # =====================================================

    search.bind(
        "<KeyRelease>",
        lambda event: load_archive()
    )

    type_filter.configure(
        command=lambda value: load_archive()
    )

    refresh_button.configure(
        command=load_archive
    )

    restore_button.configure(
        command=restore_selected
    )

    view_button.configure(
        command=view_selected_event
    )

    delete_permanent_button.configure(
        command=delete_selected_permanently
    )

    tree.bind(
        "<<TreeviewSelect>>",
        update_action_buttons
    )

    # =====================================================
    # Initial Load
    # =====================================================

    load_archive()