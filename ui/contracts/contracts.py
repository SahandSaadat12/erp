import customtkinter as ctk
from tkinter import ttk

from config import *
from ui.common.guard import guarded, perm_state

from persiantools.jdatetime import JalaliDate

from .add_contracts import add_contract
from .edit_contract import edit_contract
from .delete_contract import delete_contract
from .view_contract import view_contract
# from .refresh_contracts import refresh_contracts
from utils.date_converter import (
    gregorian_to_jalali,
    jalali_to_gregorian
)


def create_contracts(contracts_frame, database, current_user=None):

    # ===============================
    # Clear Page
    # ===============================

    for widget in contracts_frame.winfo_children():
        widget.destroy()

    contracts_frame.grid_columnconfigure(
        0,
        weight=1
    )

    contracts_frame.grid_rowconfigure(
        3,
        weight=1
    )

    # ===============================
    # Title
    # ===============================

    title = ctk.CTkLabel(
        contracts_frame,
        text="Contracts",
        font=FONT_TITLE,
        text_color=TEXT
    )

    title.grid(
        row=0,
        column=0,
        sticky="w",
        padx=10,
        pady=(10, 5)
    )

    # ===============================
    # Search & Filters
    # ===============================

    search_frame = ctk.CTkFrame(
        contracts_frame,
        fg_color=HEADER,
        corner_radius=12,
        border_width=1,
        border_color=BORDER
    )

    search_frame.grid(
        row=1,
        column=0,
        sticky="ew",
        padx=10,
        pady=(0, 10)
    )

    search_frame.grid_columnconfigure(
        0,
        weight=1
    )

    # ===============================
    # Search
    # ===============================

    search_entry = ctk.CTkEntry(
        search_frame,
        placeholder_text="🔍 Search Contract...",
        font=FONT_NORMAL,
        height=40
    )

    search_entry.grid(
        row=0,
        column=0,
        sticky="ew",
        padx=(12, 10),
        pady=12
    )

    # ===============================
    # Contract Statuses
    # ===============================

    statuses = database.get_contract_statuses()

    status_names = [
        "All Status"
    ]

    for status in statuses:

        if status[0] not in status_names:
            status_names.append(status[0])

    status_combo = ctk.CTkComboBox(
        search_frame,
        values=status_names,
        width=170,
        font=FONT_NORMAL
    )

    status_combo.set(
        "All Status"
    )

    status_combo.grid(
        row=0,
        column=1,
        padx=(0, 10),
        pady=12
    )

    # ===============================
    # Project Filter
    # ===============================

    projects = database.get_contract_projects()

    project_names = [
        "All Projects"
    ]

    for project in projects:

        if project[1] not in project_names:
            project_names.append(project[1])

    project_combo = ctk.CTkComboBox(
        search_frame,
        values=project_names,
        width=190,
        font=FONT_NORMAL
    )

    project_combo.set(
        "All Projects"
    )

    project_combo.grid(
        row=0,
        column=2,
        padx=(0, 12),
        pady=12
    )

    # ===============================
    # Dynamic Contract Years
    # ===============================

    all_contracts_for_years = database.get_contracts()

    jalali_years = set()

    for contract in all_contracts_for_years:

        contract_date = contract[6]

        if not contract_date:
            continue

        try:

            jalali_date = gregorian_to_jalali(
                contract_date
            )

            year = int(
                jalali_date.split("/")[0]
            )

            jalali_years.add(year)

        except (
            ValueError,
            TypeError
        ):
            pass

    if jalali_years:

        minimum_year = min(jalali_years)
        maximum_year = max(jalali_years)

        year_values = [
            "All Years"
        ]

        for year in range(
            maximum_year,
            minimum_year - 1,
            -1
        ):

            year_values.append(
                str(year)
            )

    else:

        year_values = [
            "All Years"
        ]

    # ===============================
    # Year Filter
    # ===============================

    year_combo = ctk.CTkComboBox(
        search_frame,
        values=year_values,
        width=125,
        font=FONT_NORMAL
    )

    year_combo.set(
        "All Years"
    )

    year_combo.grid(
        row=0,
        column=3,
        padx=(0, 8),
        pady=12
    )

    # ===============================
    # Period Filter
    # ===============================

    period_values = [
        "All Periods",
        "First Half",
        "Second Half"
    ]

    period_combo = ctk.CTkComboBox(
        search_frame,
        values=period_values,
        width=135,
        font=FONT_NORMAL
    )

    period_combo.set(
        "All Periods"
    )

    period_combo.grid(
        row=0,
        column=4,
        padx=(0, 12),
        pady=12
    )

    # ===============================
    # Clear Filters
    # ===============================

    def clear_filters():

        search_entry.delete(0, "end")

        status_combo.set("All Status")
        project_combo.set("All Projects")
        year_combo.set("All Years")
        period_combo.set("All Periods")

        search_contracts()

    # ===============================
    # Clear Button
    # ===============================

    clear_button = ctk.CTkButton(
        search_frame,
        text="✕ Clear",
        width=90,
        height=40,
        font=FONT_NORMAL,
        fg_color=VIEW,
        hover_color=VIEW_HOVER,
        command=clear_filters
    )

    clear_button.grid(
        row=0,
        column=5,
        padx=(0, 12),
        pady=12
    )


    # ===============================
    # Table Frame
    # ===============================

    table_frame = ctk.CTkFrame(
        contracts_frame,
        fg_color=CARD,
        corner_radius=12,
        border_width=1,
        border_color=BORDER
    )

    table_frame.grid(
        row=3,
        column=0,
        sticky="nsew",
        padx=10,
        pady=(0, 10)
    )

    table_frame.grid_rowconfigure(
        0,
        weight=1
    )

    table_frame.grid_columnconfigure(
        0,
        weight=1
    )

    # ===============================
    # Treeview Style
    # ===============================

    style = ttk.Style()

    style.configure(
        "Contracts.Treeview",
        background=TREE_BACKGROUND,
        foreground=TREE_FOREGROUND,
        fieldbackground=TREE_BACKGROUND,
        rowheight=TREE_ROW_HEIGHT,
        font=TREE_FONT
    )

    style.configure(
        "Contracts.Treeview.Heading",
        background=TREE_HEADER_BACKGROUND,
        foreground=TREE_HEADER_FOREGROUND,
        font=TREE_HEADER_FONT
    )

    style.map(
        "Contracts.Treeview",
        background=[
            ("selected", TREE_SELECTED)
        ],
        foreground=[
            ("selected", TEXT)
        ]
    )

    # ===============================
    # Scrollbars
    # ===============================

    tree_scroll_y = ttk.Scrollbar(
        table_frame,
        orient="vertical"
    )

    tree_scroll_x = ttk.Scrollbar(
        table_frame,
        orient="horizontal"
    )

    # ===============================
    # Treeview
    # ===============================

    tree = ttk.Treeview(
        table_frame,
        columns=(
            "id",
            "name",
            "number",
            "project",
            "client",
            "value",
            "date",
            "status"
        ),
        show="headings",
        style="Contracts.Treeview",
        yscrollcommand=tree_scroll_y.set,
        xscrollcommand=tree_scroll_x.set
    )

    tree_scroll_y.configure(
        command=tree.yview
    )

    tree_scroll_x.configure(
        command=tree.xview
    )

    tree.grid(
        row=0,
        column=0,
        sticky="nsew"
    )

    tree_scroll_y.grid(
        row=0,
        column=1,
        sticky="ns"
    )

    tree_scroll_x.grid(
        row=1,
        column=0,
        sticky="ew"
    )

    # ===============================
    # Headers
    # ===============================

    tree.heading(
        "id",
        text="No"
    )

    tree.heading(
        "name",
        text="Name"
    )

    tree.heading(
        "number",
        text="Number"
    )

    tree.heading(
        "project",
        text="Project"
    )

    tree.heading(
        "client",
        text="Client"
    )

    tree.heading(
        "value",
        text="Value"
    )

    tree.heading(
        "date",
        text="Date"
    )

    tree.heading(
        "status",
        text="Status"
    )

    # ===============================
    # Columns
    # ===============================

    tree.column(
        "id",
        width=70,
        anchor="center"
    )

    tree.column(
        "name",
        width=240
    )

    tree.column(
        "project",
        width=200
    )

    tree.column(
        "client",
        width=180
    )

    tree.column(
        "value",
        width=130,
        anchor="center"
    )

    tree.column(
        "number",
        width=150,
        anchor="center"
    )

    tree.column(
        "date",
        width=120,
        anchor="center"
    )

    tree.column(
        "status",
        width=130,
        anchor="center"
    )

    # ===============================
    # Footer
    # ===============================

    footer = ctk.CTkFrame(
        contracts_frame,
        fg_color="transparent"
    )

    footer.grid(
        row=4,
        column=0,
        sticky="ew",
        padx=10,
        pady=(0, 5)
    )

    footer.grid_columnconfigure(
        0,
        weight=1
    )

    count_label = ctk.CTkLabel(
        footer,
        text="Showing : 0 Contracts",
        text_color=TEXT2,
        font=FONT_NORMAL
    )

    count_label.grid(
        row=0,
        column=0,
        sticky="w"
    )

    # ===============================
    # Update Count
    # ===============================

    def update_count():

        count_label.configure(
            text=f"Showing : {len(tree.get_children())} Contracts"
        )

    # ===============================
    # Load Contracts
    # ===============================

    def load_contracts(contracts):

        for item in tree.get_children():
            tree.delete(item)

        for contract in contracts:
            contract_date = contract[6] or "-"

            if contract_date != "-":

                try:
                    contract_date = gregorian_to_jalali(
                        contract_date
                    )

                except Exception:
                    pass

            tree.insert(
                "",
                "end",
                values=(
                    contract[0],
                    contract[1] or "-",
                    contract[2] or "-",
                    contract[3] or "-",
                    contract[4] or "-",
                    contract[5] or "-",
                    contract_date,
                    contract[7] or "-"
                )
            )

        update_count()

    # ===============================
    # Search / Filters
    # ===============================

    def search_contracts(event=None):

        keyword = search_entry.get().strip()

        selected_project = project_combo.get()

        selected_status = status_combo.get()

        selected_year = year_combo.get()

        selected_period = period_combo.get()

        # ==================================================
        # Date Range
        # ==================================================

        date_start = None
        date_end = None

        if selected_year != "All Years":

            try:

                year = int(
                    selected_year
                )

                # --------------------------------------------------
                # First Half
                # --------------------------------------------------

                if selected_period == "First Half":

                    date_start = f"{year}/01/01"
                    date_end = f"{year}/06/31"

                # --------------------------------------------------
                # Second Half
                # --------------------------------------------------

                elif selected_period == "Second Half":

                    date_start = f"{year}/07/01"

                    last_day = (
                        30
                        if JalaliDate.is_leap(year)
                        else 29
                    )

                    date_end = (
                        f"{year}/12/{last_day}"
                    )

                # --------------------------------------------------
                # Whole Year
                # --------------------------------------------------

                else:

                    date_start = f"{year}/01/01"

                    last_day = (
                        30
                        if JalaliDate.is_leap(year)
                        else 29
                    )

                    date_end = (
                        f"{year}/12/{last_day}"
                    )

                # Convert Jalali → Gregorian

                from utils.date_converter import jalali_to_gregorian

                date_start = jalali_to_gregorian(
                    date_start
                )

                date_end = jalali_to_gregorian(
                    date_end
                )

            except (
                ValueError,
                TypeError
            ):

                date_start = None
                date_end = None

        # ==================================================
        # Get Contracts
        # ==================================================

        if (
            keyword == ""
            and selected_project == "All Projects"
            and selected_status == "All Status"
            and selected_year == "All Years"
            and selected_period == "All Periods"
        ):

            contracts = database.get_contracts()

        else:

            contracts = database.search_contracts(
                keyword,
                selected_project,
                selected_status,
                date_start,
                date_end
            )

        load_contracts(
            contracts
        )

    # ===============================
    # Search Events
    # ===============================

    search_entry.bind(
        "<KeyRelease>",
        search_contracts
    )

    status_combo.configure(
        command=lambda choice: search_contracts()
    )

    project_combo.configure(
        command=lambda choice: search_contracts()
    )

    year_combo.configure(
        command=lambda choice: search_contracts()
    )

    period_combo.configure(
        command=lambda choice: search_contracts()
    )

    # ===============================
    # Toolbar
    # ===============================

    toolbar = ctk.CTkFrame(
        contracts_frame,
        fg_color="transparent"
    )

    toolbar.grid(
        row=2,
        column=0,
        sticky="w",
        padx=10,
        pady=(0, 10)
    )

    # ===============================
    # Add
    # ===============================

    ctk.CTkButton(
        toolbar,
        text="➕ Add",
        state=perm_state(current_user, "contracts.create"),
        width=120,
        height=38,
        font=FONT_NORMAL,
        fg_color=GREEN,
        hover_color=GREEN_HOVER,
        command=guarded(current_user, "contracts.create", "add contracts", lambda: add_contract(
            on_saved=search_contracts
        ))
    ).grid(
        row=0,
        column=0,
        padx=(0, 8)
    )

    # ===============================
    # Edit
    # ===============================

    ctk.CTkButton(
        toolbar,
        text="✏ Edit",
        state=perm_state(current_user, "contracts.edit"),
        width=120,
        height=38,
        font=FONT_NORMAL,
        fg_color=BLUE,
        hover_color=BLUE_HOVER,
        command=guarded(current_user, "contracts.edit", "edit contracts", lambda: edit_contract(
            tree,
            search_contracts
        ))
    ).grid(
        row=0,
        column=1,
        padx=(0, 8)
    )

    # ===============================
    # Delete
    # ===============================

    ctk.CTkButton(
        toolbar,
        text="🗑 Delete",
        state=perm_state(current_user, "contracts.delete"),
        width=120,
        height=38,
        font=FONT_NORMAL,
        fg_color=DELETE,
        hover_color=DELETE_HOVER,
        command=guarded(current_user, "contracts.delete", "delete contracts", lambda: delete_contract(
            tree,
            search_contracts
        ))
    ).grid(
        row=0,
        column=2,
        padx=(0, 8)
    )

    # ===============================
    # View
    # ===============================

    ctk.CTkButton(
        toolbar,
        text="👁 View",
        state=perm_state(current_user, "contracts.view"),
        width=120,
        height=38,
        font=FONT_NORMAL,
        fg_color=VIEW,
        hover_color=VIEW_HOVER,
        command=guarded(current_user, "contracts.view", "view contracts", lambda: view_contract(
            tree
        ))
    ).grid(
        row=0,
        column=3,
        padx=(0, 8)
    )

    # ===============================
    # Refresh
    # ===============================

    def refresh_button():
        search_contracts()

    ctk.CTkButton(
        toolbar,
        text="🔄 Refresh",
        width=120,
        height=38,
        font=FONT_NORMAL,
        command=refresh_button
    ).grid(
        row=0,
        column=4
    )

    # ===============================
    # Initial Data
    # ===============================

    load_contracts(
        database.get_contracts()
    )