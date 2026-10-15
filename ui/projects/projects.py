import customtkinter as ctk
from tkinter import ttk, messagebox

from persiantools.jdatetime import JalaliDate

from config import *

from .add_projects import add_project
from .edit_projects import edit_project
from .delete_projects import delete_project
from .view_project import view_project
from .refresh_projects import refresh_projects
from utils.date_converter import (
    gregorian_to_jalali,
    jalali_to_gregorian
)


def create_projects(projects_frame, database, current_user=None):

    # ===============================
    # Clear Page
    # ===============================

    for widget in projects_frame.winfo_children():
        widget.destroy()

    projects_frame.grid_columnconfigure(
        0,
        weight=1
    )

    projects_frame.grid_rowconfigure(
        3,
        weight=1
    )

    # ===============================
    # Title
    # ===============================

    title = ctk.CTkLabel(
        projects_frame,
        text="Projects",
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
    # ===============================
    # Search & Filters
    # ===============================

    search_frame = ctk.CTkFrame(
        projects_frame,
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
        placeholder_text="🔍 Search Project...",
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
    # Status Filter
    # ===============================

    statuses = database.get_project_statuses()

    status_names = [
        "All Status"
    ]

    for status in statuses:

        if status[0] not in status_names:
            status_names.append(status[0])

    status_combo = ctk.CTkComboBox(
        search_frame,
        values=status_names,
        width=150,
        font=FONT_NORMAL
    )

    status_combo.set(
        "All Status"
    )

    status_combo.grid(
        row=0,
        column=1,
        padx=(0, 8),
        pady=12
    )

    # ===============================
    # Manager Filter
    # ===============================

    managers = database.get_managers()

    manager_names = [
        "All Managers"
    ]

    for manager in managers:

        if manager[1] not in manager_names:
            manager_names.append(manager[1])

    manager_combo = ctk.CTkComboBox(
        search_frame,
        values=manager_names,
        width=160,
        font=FONT_NORMAL
    )

    manager_combo.set(
        "All Managers"
    )

    manager_combo.grid(
        row=0,
        column=2,
        padx=(0, 8),
        pady=12
    )

    # ===============================
    # Dynamic Years
    # ===============================

    all_projects_for_years = database.get_projects()

    jalali_years = set()

    for project in all_projects_for_years:

        start_date = project[6]
        end_date = project[7]

        for project_date in (
            start_date,
            end_date
        ):

            if not project_date:
                continue

            try:

                jalali_date = gregorian_to_jalali(
                    project_date
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

    # ------------------------------------------------------
    # Fill missing years between minimum and maximum
    # ------------------------------------------------------

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
        padx=(0, 8),
        pady=12
    )

    # ===============================
    # Clear Filters
    # ===============================

    clear_button = ctk.CTkButton(
        search_frame,
        text="✕ Clear",
        width=80,
        height=40,
        font=FONT_NORMAL,
        fg_color=VIEW,
        hover_color=VIEW_HOVER
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
        projects_frame,
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
        "Projects.Treeview",
        background=TREE_BACKGROUND,
        foreground=TREE_FOREGROUND,
        fieldbackground=TREE_BACKGROUND,
        rowheight=TREE_ROW_HEIGHT,
        font=TREE_FONT
    )

    style.configure(
        "Projects.Treeview.Heading",
        background=TREE_HEADER_BACKGROUND,
        foreground=TREE_HEADER_FOREGROUND,
        font=TREE_HEADER_FONT
    )

    style.map(
        "Projects.Treeview",
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
            "code",
            "name",
            "client",
            "manager",
            "progress",
            "status",
            "start",
            "end"
        ),
        show="headings",
        style="Projects.Treeview",
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
    # Treeview Headers
    # ===============================

    tree.heading(
        "code",
        text="Code"
    )

    tree.heading(
        "name",
        text="Project"
    )

    tree.heading(
        "client",
        text="Client"
    )

    tree.heading(
        "manager",
        text="Manager"
    )

    tree.heading(
        "progress",
        text="Progress"
    )

    tree.heading(
        "status",
        text="Status"
    )

    tree.heading(
        "start",
        text="Start"
    )

    tree.heading(
        "end",
        text="End"
    )

    # ===============================
    # Treeview Columns
    # ===============================

    tree.column(
        "code",
        width=100,
        anchor="center"
    )

    tree.column(
        "name",
        width=250
    )

    tree.column(
        "client",
        width=180
    )

    tree.column(
        "manager",
        width=170
    )

    tree.column(
        "progress",
        width=100,
        anchor="center"
    )

    tree.column(
        "status",
        width=130,
        anchor="center"
    )

    tree.column(
        "start",
        width=120,
        anchor="center"
    )

    tree.column(
        "end",
        width=120,
        anchor="center"
    )

    # ===============================
    # Footer
    # ===============================

    footer = ctk.CTkFrame(
        projects_frame,
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
        text="Showing : 0 Projects",
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
            text=f"Showing : {len(tree.get_children())} Projects"
        )

    # ===============================
    # Load Projects
    # ===============================

    def load_projects(projects):

        for item in tree.get_children():
            tree.delete(item)

        for project in projects:
            tree.insert(
                "",
                "end",
                values=(
                    project[0],
                    project[1],
                    project[2] or "-",
                    project[3] or "-",
                    f"{project[4]}%",
                    project[5] or "-",
                    gregorian_to_jalali(project[6])
                    if project[6]
                    else "-",
                    gregorian_to_jalali(project[7])
                    if project[7]
                    else "-"
                )
            )

        update_count()

    # ===============================
    # Search / Filters
    # ===============================

    def search_projects(event=None):

        keyword = search_entry.get().strip()

        selected_manager = manager_combo.get()

        selected_status = status_combo.get()

        selected_year = year_combo.get()

        selected_period = period_combo.get()

        # ==================================================
        # Default Date Range
        # ==================================================

        date_start = None
        date_end = None

        # ==================================================
        # Year / Period Filter
        # ==================================================

        if selected_year != "All Years":

            try:

                year = int(
                    selected_year
                )

                # --------------------------------------------------
                # First Half
                # --------------------------------------------------

                if selected_period == "First Half":

                    date_start = jalali_to_gregorian(
                        f"{year}/01/01"
                    )

                    date_end = jalali_to_gregorian(
                        f"{year}/06/31"
                    )

                # --------------------------------------------------
                # Second Half
                # --------------------------------------------------

                elif selected_period == "Second Half":

                    date_start = jalali_to_gregorian(
                        f"{year}/07/01"
                    )

                    last_day = (
                        30
                        if JalaliDate.is_leap(year)
                        else 29
                    )

                    date_end = jalali_to_gregorian(
                        f"{year}/12/{last_day}"
                    )

                # --------------------------------------------------
                # Whole Year
                # --------------------------------------------------

                else:

                    date_start = jalali_to_gregorian(
                        f"{year}/01/01"
                    )

                    last_day = (
                        30
                        if JalaliDate.is_leap(year)
                        else 29
                    )

                    date_end = jalali_to_gregorian(
                        f"{year}/12/{last_day}"
                    )

            except (
                    ValueError,
                    TypeError
            ):

                date_start = None
                date_end = None
        # ==================================================
        # Exact Jalali Date Search
        # ==================================================

        if keyword:

            normalized_keyword = (
                keyword
                .replace("-", "/")
                .strip()
            )

            parts = normalized_keyword.split("/")

            # --------------------------------------------------
            # Full Jalali Date
            # Example: 1405/03/15
            # --------------------------------------------------

            if len(parts) == 3:

                try:

                    input_year = int(parts[0])
                    input_month = int(parts[1])
                    input_day = int(parts[2])

                    # Validate the Jalali date
                    JalaliDate(
                        input_year,
                        input_month,
                        input_day
                    )

                    exact_date = jalali_to_gregorian(
                        f"{input_year:04d}/"
                        f"{input_month:02d}/"
                        f"{input_day:02d}"
                    )

                    date_start = exact_date
                    date_end = exact_date

                except (
                        ValueError,
                        TypeError
                ):

                    # Invalid date -> keep normal text search
                    pass

            # --------------------------------------------------
            # Jalali Year
            # Example: 1405
            # --------------------------------------------------

            elif (
                    len(parts) == 1
                    and normalized_keyword.isdigit()
                    and len(normalized_keyword) == 4
            ):

                try:

                    input_year = int(
                        normalized_keyword
                    )

                    JalaliDate(
                        input_year,
                        1,
                        1
                    )

                    date_start = jalali_to_gregorian(
                        f"{input_year}/01/01"
                    )

                    last_day = (
                        30
                        if JalaliDate.is_leap(input_year)
                        else 29
                    )

                    date_end = jalali_to_gregorian(
                        f"{input_year}/12/{last_day}"
                    )

                except (
                        ValueError,
                        TypeError
                ):

                    pass

        # ==================================================
        # Get Projects
        # ==================================================

        if (
            keyword == ""
            and selected_manager == "All Managers"
            and selected_status == "All Status"
            and selected_year == "All Years"
            and selected_period == "All Periods"
        ):

            projects = database.get_projects()

        else:

            projects = database.search_projects(
                keyword,
                selected_manager,
                selected_status,
                date_start,
                date_end
            )

        load_projects(
            projects
        )


    def clear_filters():

        search_entry.delete(
            0,
            "end"
        )

        status_combo.set(
            "All Status"
        )

        manager_combo.set(
            "All Managers"
        )

        year_combo.set(
            "All Years"
        )

        period_combo.set(
            "All Periods"
        )

        search_projects()


    clear_button.configure(
        command=clear_filters
    )



    # ===============================
    # Search Events
    # ===============================

    search_entry.bind(
        "<KeyRelease>",
        search_projects
    )

    status_combo.configure(
        command=lambda choice: search_projects()
    )

    manager_combo.configure(
        command=lambda choice: search_projects()
    )

    year_combo.configure(
        command=lambda choice: search_projects()
    )

    period_combo.configure(
        command=lambda choice: search_projects()
    )

    # ===============================
    # Toolbar
    # ===============================

    toolbar = ctk.CTkFrame(
        projects_frame,
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

    can_create = database.has_permission(current_user, "projects.create")
    can_edit = database.has_permission(current_user, "projects.edit")
    can_delete = database.has_permission(current_user, "projects.delete")

    def guarded_add():
        if not can_create:
            messagebox.showwarning("Projects", "You don't have permission to add projects.")
            return
        add_project(database)

    ctk.CTkButton(
        toolbar,
        text="➕ Add",
        width=120,
        height=38,
        font=FONT_NORMAL,
        fg_color=GREEN,
        hover_color=GREEN_HOVER,
        state="normal" if can_create else "disabled",
        command=guarded_add
    ).grid(
        row=0,
        column=0,
        padx=(0, 8)
    )

    # ===============================
    # Edit
    # ===============================

    def guarded_edit():
        if not can_edit:
            messagebox.showwarning("Projects", "You don't have permission to edit projects.")
            return
        edit_project(database, tree)

    ctk.CTkButton(
        toolbar,
        text="✏ Edit",
        width=120,
        height=38,
        font=FONT_NORMAL,
        fg_color=BLUE,
        hover_color=BLUE_HOVER,
        state="normal" if can_edit else "disabled",
        command=guarded_edit
    ).grid(
        row=0,
        column=1,
        padx=(0, 8)
    )

    # ===============================
    # Delete
    # ===============================

    def guarded_delete():
        if not can_delete:
            messagebox.showwarning("Projects", "You don't have permission to delete projects.")
            return
        delete_project(database, tree)

    ctk.CTkButton(
        toolbar,
        text="🗑 Delete",
        width=120,
        height=38,
        font=FONT_NORMAL,
        fg_color=DELETE,
        hover_color=DELETE_HOVER,
        state="normal" if can_delete else "disabled",
        command=guarded_delete
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
        width=120,
        height=38,
        font=FONT_NORMAL,
        fg_color=VIEW,
        hover_color=VIEW_HOVER,
        command=lambda: view_project(tree, current_user, database)
    ).grid(
        row=0,
        column=3,
        padx=(0, 8)
    )

    # ===============================
    # Refresh
    # ===============================

    def refresh_button():

        refresh_projects(
            tree,
            database
        )

        update_count()

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

    load_projects(
        database.get_projects()
    )