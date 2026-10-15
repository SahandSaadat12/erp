import customtkinter as ctk
from tkinter import ttk, messagebox

from config import *
from ui.common.guard import guarded, perm_state
from db.lookups import get_values as get_lookup_values

from persiantools.jdatetime import JalaliDate

from utils.date_converter import (
    gregorian_to_jalali,
    jalali_to_gregorian
)

from .delete_expense import delete_selected_expense
from .add_expense import open_add_expense
from .edit_expense import open_edit_expense
from .view_expense import view_expense

from database import (
    search_expenses,
    get_expense_projects,
    get_expense_total
)


def create_expenses(expenses_frame, current_user=None):

    # ==========================================================
    # Clear Page
    # ==========================================================

    for widget in expenses_frame.winfo_children():
        widget.destroy()

    expenses_frame.grid_columnconfigure(
        0,
        weight=1
    )

    expenses_frame.grid_rowconfigure(
        3,
        weight=1
    )

    # ==========================================================
    # Title
    # ==========================================================

    title = ctk.CTkLabel(
        expenses_frame,
        text="Expenses",
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

    # ==========================================================
    # Search & Filters
    # ==========================================================

    filter_frame = ctk.CTkFrame(
        expenses_frame,
        fg_color=HEADER,
        corner_radius=12,
        border_width=1,
        border_color=BORDER
    )

    filter_frame.grid(
        row=1,
        column=0,
        sticky="ew",
        padx=10,
        pady=(0, 10)
    )

    filter_frame.grid_columnconfigure(
        0,
        weight=1
    )

    # ==========================================================
    # Search
    # ==========================================================

    search = ctk.CTkEntry(
        filter_frame,
        placeholder_text="🔍 Search Expense...",
        font=FONT_NORMAL,
        height=40
    )

    search.grid(
        row=0,
        column=0,
        sticky="ew",
        padx=(12, 10),
        pady=12
    )

    # ==========================================================
    # Project Filter
    # ==========================================================

    project_values = [
        "All Projects"
    ]

    try:

        projects = get_expense_projects()

        for project_id, project_name in projects:

            if (
                project_name
                and project_name not in project_values
            ):
                project_values.append(
                    project_name
                )

    except Exception:
        # Projects filter just stays "All Projects" if lookup data can't
        # be loaded right now - the page itself still renders.
        pass

    project = ctk.CTkComboBox(
        filter_frame,
        values=project_values,
        width=190,
        font=FONT_NORMAL
    )

    project.set(
        "All Projects"
    )

    project.grid(
        row=0,
        column=1,
        padx=(0, 10),
        pady=12
    )

    # ==========================================================
    # Category Filter
    # ==========================================================

    category = ctk.CTkComboBox(
        filter_frame,
        values=["All"] + get_lookup_values("expense_category"),
        width=170,
        font=FONT_NORMAL
    )

    category.set(
        "All"
    )

    category.grid(
        row=0,
        column=2,
        padx=(0, 10),
        pady=12
    )

    # ==========================================================
    # Status Filter
    # ==========================================================

    status = ctk.CTkComboBox(
        filter_frame,
        values=["All"] + get_lookup_values("expense_status"),
        width=150,
        font=FONT_NORMAL
    )

    status.set(
        "All"
    )

    status.grid(
        row=0,
        column=3,
        padx=(0, 10),
        pady=12
    )

    # ==========================================================
    # Dynamic Expense Years
    # ==========================================================

    all_expenses_for_years = search_expenses()

    jalali_years = set()

    for expense in all_expenses_for_years:

        expense_date = expense[2]

        if not expense_date:
            continue

        try:

            jalali_date = gregorian_to_jalali(
                expense_date
            )

            year = int(
                jalali_date.split("/")[0]
            )

            jalali_years.add(
                year
            )

        except (
            ValueError,
            TypeError
        ):
            pass

    if jalali_years:

        minimum_year = min(
            jalali_years
        )

        maximum_year = max(
            jalali_years
        )

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

    # ==========================================================
    # Year Filter
    # ==========================================================

    year = ctk.CTkComboBox(
        filter_frame,
        values=year_values,
        width=125,
        font=FONT_NORMAL
    )

    year.set(
        "All Years"
    )

    year.grid(
        row=0,
        column=4,
        padx=(0, 8),
        pady=12
    )

    # ==========================================================
    # Period Filter
    # ==========================================================

    period = ctk.CTkComboBox(
        filter_frame,
        values=[
            "All Periods",
            "First Half",
            "Second Half"
        ],
        width=135,
        font=FONT_NORMAL
    )

    period.set(
        "All Periods"
    )

    period.grid(
        row=0,
        column=5,
        padx=(0, 10),
        pady=12
    )

    # ==========================================================
    # Table Frame
    # ==========================================================

    table_frame = ctk.CTkFrame(
        expenses_frame,
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

    # ==========================================================
    # Treeview Style
    # ==========================================================

    style = ttk.Style()

    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure(
        "Expenses.Treeview",
        background=TREE_BACKGROUND,
        foreground=TREE_FOREGROUND,
        fieldbackground=TREE_BACKGROUND,
        rowheight=TREE_ROW_HEIGHT,
        font=TREE_FONT
    )

    style.configure(
        "Expenses.Treeview.Heading",
        background=TREE_HEADER_BACKGROUND,
        foreground=TREE_HEADER_FOREGROUND,
        font=TREE_HEADER_FONT
    )

    style.map(
        "Expenses.Treeview",
        background=[
            ("selected", TREE_SELECTED)
        ],
        foreground=[
            ("selected", TEXT)
        ]
    )

    # ==========================================================
    # Scrollbars
    # ==========================================================

    tree_scroll_y = ttk.Scrollbar(
        table_frame,
        orient="vertical"
    )

    tree_scroll_x = ttk.Scrollbar(
        table_frame,
        orient="horizontal"
    )

    # ==========================================================
    # Treeview
    # ==========================================================

    tree = ttk.Treeview(
        table_frame,
        columns=(
            "id",
            "date",
            "project",
            "phase",
            "title",
            "category",
            "description",
            "amount",
            "paid_by",
            "status"
        ),
        show="headings",
        style="Expenses.Treeview",
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

    # ==========================================================
    # Headers
    # ==========================================================

    tree.heading(
        "id",
        text="No"
    )

    tree.heading(
        "date",
        text="Date"
    )

    tree.heading(
        "project",
        text="Project"
    )

    tree.heading(
        "phase",
        text="Phase"
    )

    tree.heading(
        "title",
        text="Title"
    )

    tree.heading(
        "category",
        text="Category"
    )

    tree.heading(
        "description",
        text="Description"
    )

    tree.heading(
        "amount",
        text="Amount"
    )

    tree.heading(
        "paid_by",
        text="Paid By"
    )

    tree.heading(
        "status",
        text="Status"
    )

    # ==========================================================
    # Columns
    # ==========================================================

    tree.column(
        "id",
        width=70,
        anchor="center"
    )

    tree.column(
        "date",
        width=120,
        anchor="center"
    )

    tree.column(
        "project",
        width=200
    )

    tree.column(
        "phase",
        width=170
    )

    tree.column(
        "title",
        width=220
    )

    tree.column(
        "category",
        width=130,
        anchor="center"
    )

    tree.column(
        "description",
        width=280
    )

    tree.column(
        "amount",
        width=130,
        anchor="center"
    )

    tree.column(
        "paid_by",
        width=150,
        anchor="center"
    )

    tree.column(
        "status",
        width=130,
        anchor="center"
    )

    # ==========================================================
    # Footer
    # ==========================================================

    footer = ctk.CTkFrame(
        expenses_frame,
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
        1,
        weight=1
    )

    # ==========================================================
    # Total
    # ==========================================================

    total_label = ctk.CTkLabel(
        footer,
        text="Total Expenses : $0.00",
        font=FONT_CARD_TITLE,
        text_color=RED
    )

    total_label.grid(
        row=0,
        column=0,
        sticky="w"
    )

    # ==========================================================
    # Showing
    # ==========================================================

    showing = ctk.CTkLabel(
        footer,
        text="Showing : 0 Expenses",
        font=FONT_NORMAL,
        text_color=TEXT2
    )

    showing.grid(
        row=0,
        column=2,
        sticky="e"
    )

    # ==========================================================
    # Update Footer
    # ==========================================================

    def update_footer(rows):

        try:

            total = sum(
                float(row[7] or 0)
                for row in rows
            )

            formatted_total = f"{total:,.2f}"

        except (
            ValueError,
            TypeError
        ):

            formatted_total = "0.00"

        total_label.configure(
            text=f"Total Expenses : ${formatted_total}"
        )

        showing.configure(
            text=f"Showing : {len(rows)} Expenses"
        )

    # ==========================================================
    # Load Expenses
    # ==========================================================

    def load_expenses():

        for item in tree.get_children():
            tree.delete(item)

        keyword = search.get().strip()

        selected_project = project.get()

        selected_category = category.get()

        selected_status = status.get()

        selected_year = year.get()

        selected_period = period.get()

        # ======================================================
        # Date Range
        # ======================================================

        date_start = None
        date_end = None

        if selected_year != "All Years":

            try:

                selected_year_number = int(
                    selected_year
                )

                # ------------------------------------------------
                # First Half
                # ------------------------------------------------

                if selected_period == "First Half":

                    jalali_start = (
                        f"{selected_year_number}/01/01"
                    )

                    jalali_end = (
                        f"{selected_year_number}/06/31"
                    )

                # ------------------------------------------------
                # Second Half
                # ------------------------------------------------

                elif selected_period == "Second Half":

                    jalali_start = (
                        f"{selected_year_number}/07/01"
                    )

                    last_day = (
                        30
                        if JalaliDate.is_leap(
                            selected_year_number
                        )
                        else 29
                    )

                    jalali_end = (
                        f"{selected_year_number}/12/{last_day}"
                    )

                # ------------------------------------------------
                # Whole Year
                # ------------------------------------------------

                else:

                    jalali_start = (
                        f"{selected_year_number}/01/01"
                    )

                    last_day = (
                        30
                        if JalaliDate.is_leap(
                            selected_year_number
                        )
                        else 29
                    )

                    jalali_end = (
                        f"{selected_year_number}/12/{last_day}"
                    )

                # ------------------------------------------------
                # Jalali → Gregorian
                # ------------------------------------------------

                date_start = jalali_to_gregorian(
                    jalali_start
                )

                date_end = jalali_to_gregorian(
                    jalali_end
                )

            except (
                ValueError,
                TypeError
            ):

                date_start = None
                date_end = None

        # ======================================================
        # Load Data
        # ======================================================

        try:

            rows = search_expenses(
                keyword=keyword,
                project=selected_project,
                category=selected_category,
                status=selected_status,
                date_start=date_start,
                date_end=date_end
            )

        except Exception as error:

            messagebox.showerror(
                "Load Expenses",
                f"Error loading expenses:\n\n{error}"
            )

            return

        # ======================================================
        # Insert Rows
        # ======================================================

        for row in rows:

            expense_id = row[0]

            expense_title = row[1] or "-"

            expense_date = row[2] or "-"

            project_name = row[3] or "No Project"

            phase_name = row[4] or "-"

            expense_category = row[5] or "-"

            description = row[6] or "-"

            amount = row[7] or 0

            paid_by = row[8] or "-"

            expense_status = row[9] or "-"

            # --------------------------------------------------
            # Date
            # --------------------------------------------------

            if expense_date != "-":

                try:

                    expense_date = gregorian_to_jalali(
                        expense_date
                    )

                except Exception:
                    pass

            # --------------------------------------------------
            # Amount
            # --------------------------------------------------

            try:

                formatted_amount = (
                    f"{float(amount):,.2f}"
                )

            except (
                ValueError,
                TypeError
            ):

                formatted_amount = "0.00"

            # --------------------------------------------------
            # Insert
            # --------------------------------------------------

            tree.insert(
                "",
                "end",
                values=(
                    expense_id,
                    expense_date,
                    project_name,
                    phase_name,
                    expense_title,
                    expense_category,
                    description,
                    formatted_amount,
                    paid_by,
                    expense_status
                )
            )

        update_footer(
            rows
        )

    # ==========================================================
    # Clear Filters
    # ==========================================================

    def clear_filters():

        search.delete(
            0,
            "end"
        )

        project.set(
            "All Projects"
        )

        category.set(
            "All"
        )

        status.set(
            "All"
        )

        year.set(
            "All Years"
        )

        period.set(
            "All Periods"
        )

        load_expenses()

    # ==========================================================
    # Clear Button
    # ==========================================================

    clear_button = ctk.CTkButton(
        filter_frame,
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
        column=6,
        padx=(0, 12),
        pady=12
    )

    # ==========================================================
    # Search Events
    # ==========================================================

    search.bind(
        "<KeyRelease>",
        lambda event: load_expenses()
    )

    project.configure(
        command=lambda choice: load_expenses()
    )

    category.configure(
        command=lambda choice: load_expenses()
    )

    status.configure(
        command=lambda choice: load_expenses()
    )

    year.configure(
        command=lambda choice: load_expenses()
    )

    period.configure(
        command=lambda choice: load_expenses()
    )

    # ==========================================================
    # Toolbar
    # ==========================================================

    toolbar = ctk.CTkFrame(
        expenses_frame,
        fg_color="transparent"
    )

    toolbar.grid(
        row=2,
        column=0,
        sticky="w",
        padx=10,
        pady=(0, 10)
    )

    # ==========================================================
    # Add
    # ==========================================================

    add_button = ctk.CTkButton(
        toolbar,
        text="➕ Add",
        state=perm_state(current_user, "expenses.create"),
        width=120,
        height=38,
        font=FONT_NORMAL,
        fg_color=GREEN,
        hover_color=GREEN_HOVER,
        command=guarded(current_user, "expenses.create", "add expenses", lambda: open_add_expense(
            expenses_frame,
            load_expenses
        ))
    )

    add_button.grid(
        row=0,
        column=0,
        padx=(0, 8)
    )

    # ==========================================================
    # Edit
    # ==========================================================

    edit_button = ctk.CTkButton(
        toolbar,
        text="✏ Edit",
        state=perm_state(current_user, "expenses.edit"),
        width=120,
        height=38,
        font=FONT_NORMAL,
        fg_color=BLUE,
        hover_color=BLUE_HOVER,
        command=guarded(current_user, "expenses.edit", "edit expenses", lambda: edit_selected_expense())
    )

    edit_button.grid(
        row=0,
        column=1,
        padx=(0, 8)
    )

    # ==========================================================
    # Delete
    # ==========================================================

    delete_button = ctk.CTkButton(
        toolbar,
        text="🗑 Delete",
        width=120,
        height=38,
        font=FONT_NORMAL,
        fg_color=DELETE,
        hover_color=DELETE_HOVER,
        state=perm_state(current_user, "expenses.delete")
    )

    delete_button.grid(
        row=0,
        column=2,
        padx=(0, 8)
    )

    # ==========================================================
    # View
    # ==========================================================

    view_button = ctk.CTkButton(
        toolbar,
        text="👁 View",
        state=perm_state(current_user, "expenses.view"),
        width=120,
        height=38,
        font=FONT_NORMAL,
        fg_color=VIEW,
        hover_color=VIEW_HOVER,
        command=guarded(current_user, "expenses.view", "view expenses", lambda: view_expense(
            tree
        ))
    )

    view_button.grid(
        row=0,
        column=3,
        padx=(0, 8)
    )

    # ==========================================================
    # Refresh
    # ==========================================================

    refresh_button = ctk.CTkButton(
        toolbar,
        text="🔄 Refresh",
        width=120,
        height=38,
        font=FONT_NORMAL,
        command=load_expenses
    )

    refresh_button.grid(
        row=0,
        column=4
    )

    # ==========================================================
    # Selected Expense
    # ==========================================================

    def get_selected_expense_id():

        selected = tree.selection()

        if not selected:
            return None

        values = tree.item(
            selected[0],
            "values"
        )

        if not values:
            return None

        try:

            return int(
                values[0]
            )

        except (
            ValueError,
            TypeError
        ):

            return None

    # ==========================================================
    # Edit Selected Expense
    # ==========================================================

    def edit_selected_expense():

        expense_id = get_selected_expense_id()

        if expense_id is None:

            messagebox.showwarning(
                "No Selection",
                "Please select an expense first."
            )

            return

        open_edit_expense(
            expenses_frame,
            expense_id,
            load_expenses
        )

    # ==========================================================
    # Delete Command
    # ==========================================================

    delete_button.configure(
        command=guarded(
            current_user, "expenses.delete", "delete expenses",
            lambda: delete_selected_expense(
                expenses_frame,
                get_selected_expense_id(),
                load_expenses
            )
        )
    )

    # ==========================================================
    # Initial Load
    # ==========================================================

    load_expenses()