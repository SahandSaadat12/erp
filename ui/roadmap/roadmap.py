import customtkinter as ctk
from datetime import date, datetime, timedelta

from config import *
from tkinter import messagebox
from ui.common.guard import guarded, perm_state
from licensing.gate import is_feature_enabled

from database import (
    get_roadmap_projects,
    get_roadmap_phases,
    get_roadmap_project_dates,
    get_roadmap_overall_actual,
    get_roadmap_project_price,
    get_roadmap_project_actual_price,
    get_phase_actual_price
)


# ==========================================================
# Progress Colors
# ==========================================================

EXPECTED_COLOR = BLUE

ACTUAL_RED = RED
ACTUAL_ORANGE = ORANGE
ACTUAL_YELLOW = YELLOW
ACTUAL_GREEN = GREEN


# ==========================================================
# Working Days
# Friday = Holiday
# ==========================================================

def count_working_days(start, end):
    """
    Count working days from start to end.

    Start is included.
    End is excluded.

    Friday (weekday == 4) is not a working day.
    """

    if not start or not end:
        return 0

    if end <= start:
        return 0

    total_days = 0
    current = start

    while current < end:

        # Monday = 0
        # Tuesday = 1
        # Wednesday = 2
        # Thursday = 3
        # Friday = 4  -> Holiday
        # Saturday = 5
        # Sunday = 6

        if current.weekday() != 4:
            total_days += 1

        current += timedelta(days=1)

    return total_days


# ==========================================================
# Calculate Expected Progress
# ==========================================================

def calculate_expected_progress(start_date, end_date):

    if not start_date or not end_date:
        return 0

    try:
        start = datetime.strptime(
            start_date,
            "%Y-%m-%d"
        ).date()

        end = datetime.strptime(
            end_date,
            "%Y-%m-%d"
        ).date()

    except (ValueError, TypeError):
        return 0

    today = date.today()

    # ------------------------------------------------------
    # Invalid Date Range
    # ------------------------------------------------------

    if end < start:
        return 0

    # ------------------------------------------------------
    # Same Day
    # ------------------------------------------------------

    if start == end:

        if today >= end:
            return 100

        return 0

    # ------------------------------------------------------
    # Total Working Days
    # Friday is excluded
    # ------------------------------------------------------

    total_working_days = count_working_days(
        start,
        end
    )

    if total_working_days <= 0:

        if today >= end:
            return 100

        return 0

    # ------------------------------------------------------
    # Project hasn't started
    # ------------------------------------------------------

    if today <= start:
        return 0

    # ------------------------------------------------------
    # Project has finished
    # ------------------------------------------------------

    if today >= end:
        return 100

    # ------------------------------------------------------
    # Elapsed Working Days
    #
    # Today itself is not counted yet.
    # If today is Friday, it contributes 0.
    # ------------------------------------------------------

    elapsed_working_days = count_working_days(
        start,
        today
    )

    # ------------------------------------------------------
    # Expected Progress
    # ------------------------------------------------------

    expected = (
        elapsed_working_days /
        total_working_days
    ) * 100

    return max(
        0,
        min(expected, 100)
    )


# ==========================================================
# Actual Progress Color
# ==========================================================

def get_actual_color(actual, expected):

    try:
        actual = float(actual or 0)
        expected = float(expected or 0)

    except (ValueError, TypeError):
        return ACTUAL_RED

    if expected <= 0:

        if actual > 0:
            return ACTUAL_GREEN

        return ACTUAL_RED

    ratio = actual / expected

    if ratio < 0.25:
        return ACTUAL_RED

    elif ratio < 0.50:
        return ACTUAL_ORANGE

    elif ratio < 0.75:
        return ACTUAL_YELLOW

    else:
        return ACTUAL_GREEN


# ==========================================================
# Format Price
# ==========================================================

def format_price(value):

    try:
        return f"{float(value or 0):,.0f}"

    except (ValueError, TypeError):
        return "0"


# ==========================================================
# Create Price Bars
# ==========================================================

def create_price_bars(
    parent,
    row,
    column,
    expected_price,
    actual_price
):

    try:
        expected_price = float(
            expected_price or 0
        )

    except (ValueError, TypeError):
        expected_price = 0

    try:
        actual_price = float(
            actual_price or 0
        )

    except (ValueError, TypeError):
        actual_price = 0

    # ------------------------------------------------------
    # Calculate Actual Percentage
    # ------------------------------------------------------

    if expected_price > 0:

        actual_percentage = (
            actual_price /
            expected_price
        ) * 100

    else:

        actual_percentage = 0

    actual_bar_value = max(
        0,
        min(actual_percentage, 100)
    )

    actual_color = get_actual_color(
        actual_price,
        expected_price
    )

    # ------------------------------------------------------
    # Price Frame
    # ------------------------------------------------------

    price_frame = ctk.CTkFrame(
        parent,
        fg_color="transparent"
    )

    price_frame.grid(
        row=row,
        column=column,
        sticky="ne",
        padx=(30, 10),
        pady=(5, 5)
    )

    price_frame.grid_columnconfigure(
        1,
        weight=1
    )

    # ------------------------------------------------------
    # Price Title
    # ------------------------------------------------------

    ctk.CTkLabel(
        price_frame,
        text="Price",
        font=("Segoe UI", 15, "bold"),
        anchor="w"
    ).grid(
        row=0,
        column=0,
        columnspan=3,
        sticky="w",
        pady=(0, 6)
    )

    # ======================================================
    # Expected
    # ======================================================

    ctk.CTkLabel(
        price_frame,
        text="Expected",
        width=75,
        anchor="w",
        font=FONT_NORMAL
    ).grid(
        row=1,
        column=0,
        sticky="w"
    )

    expected_bar = ctk.CTkProgressBar(
        price_frame,
        width=220,
        height=14
    )

    expected_bar.grid(
        row=1,
        column=1,
        padx=8
    )

    expected_bar.set(1)

    expected_bar.configure(
        progress_color=EXPECTED_COLOR
    )

    ctk.CTkLabel(
        price_frame,
        text=f"{format_price(expected_price)} تومان",
        width=145,
        anchor="w",
        font=FONT_NORMAL
    ).grid(
        row=1,
        column=2,
        sticky="w"
    )

    # ======================================================
    # Actual
    # ======================================================

    ctk.CTkLabel(
        price_frame,
        text="Actual",
        width=75,
        anchor="w",
        font=FONT_NORMAL
    ).grid(
        row=2,
        column=0,
        sticky="w",
        pady=(5, 0)
    )

    actual_bar = ctk.CTkProgressBar(
        price_frame,
        width=220,
        height=14
    )

    actual_bar.grid(
        row=2,
        column=1,
        padx=8,
        pady=(5, 0)
    )

    actual_bar.set(
        actual_bar_value / 100
    )

    actual_bar.configure(
        progress_color=actual_color
    )

    ctk.CTkLabel(
        price_frame,
        text=f"{format_price(actual_price)} تومان",
        width=145,
        anchor="w",
        font=FONT_NORMAL
    ).grid(
        row=2,
        column=2,
        sticky="w",
        pady=(5, 0)
    )


# ==========================================================
# Create Roadmap
# ==========================================================

def create_roadmap(roadmap_frame, current_user=None):

    for widget in roadmap_frame.winfo_children():
        widget.destroy()

    roadmap_frame.grid_columnconfigure(
        0,
        weight=1
    )

    roadmap_frame.grid_rowconfigure(
        2,
        weight=1
    )

    # ======================================================
    # Title
    # ======================================================

    title = ctk.CTkLabel(
        roadmap_frame,
        text="Roadmap",
        font=FONT_TITLE
    )

    title.grid(
        row=0,
        column=0,
        sticky="w",
        padx=10,
        pady=(10, 5)
    )

    # ======================================================
    # Project Selector
    # ======================================================

    project_frame = ctk.CTkFrame(
        roadmap_frame,
        fg_color="transparent"
    )

    project_frame.grid(
        row=1,
        column=0,
        sticky="ew",
        padx=10,
        pady=10
    )

    project_frame.grid_columnconfigure(
        1,
        weight=1
    )

    ctk.CTkLabel(
        project_frame,
        text="Project :",
        font=FONT_NORMAL
    ).grid(
        row=0,
        column=0,
        sticky="w",
        padx=10
    )

    projects = get_roadmap_projects()

    project_values = [
        f"{project[1]} - {project[2]}"
        for project in projects
    ]

    project_box = ctk.CTkComboBox(
        project_frame,
        values=project_values,
        width=350,
        state="readonly"
    )

    project_box.grid(
        row=0,
        column=1,
        sticky="w"
    )

    # ======================================================
    # Export to Excel (charts + numbers)
    # ======================================================

    def export_excel():

        selected = project_box.get()

        if selected not in project_values:
            messagebox.showwarning("Export", "Please select a project first.")
            return

        from utils.roadmap_export import export_roadmap_dialog

        export_roadmap_dialog(
            roadmap_frame,
            projects[project_values.index(selected)][0]
        )

    # Excel export is a separately licensed feature (license feature: excel_export)
    if is_feature_enabled("excel_export"):
        ctk.CTkButton(
            project_frame,
            text="📊 Export Excel",
            width=150,
            height=34,
            font=FONT_NORMAL,
            fg_color=GREEN,
            hover_color=GREEN_HOVER,
            state=perm_state(current_user, "roadmap.view"),
            command=guarded(current_user, "roadmap.view", "export the roadmap", export_excel)
        ).grid(
            row=0,
            column=2,
            padx=(12, 0)
        )

    # ======================================================
    # Content
    # ======================================================

    content_frame = ctk.CTkScrollableFrame(
        roadmap_frame,
        fg_color="transparent"
    )

    content_frame.grid(
        row=2,
        column=0,
        sticky="nsew",
        padx=10,
        pady=10
    )

    content_frame.grid_columnconfigure(
        0,
        weight=1
    )

    # ======================================================
    # Phases Card
    # ======================================================

    phases_frame = ctk.CTkFrame(
        content_frame,
        fg_color=CARD,
        corner_radius=12,
        border_width=1,
        border_color=BORDER
    )

    phases_frame.grid(
        row=0,
        column=0,
        sticky="ew",
        pady=(0, 10)
    )

    phases_frame.grid_columnconfigure(
        0,
        weight=1
    )

    # ======================================================
    # Overall Card
    # ======================================================

    overall = ctk.CTkFrame(
        content_frame,
        fg_color=CARD,
        corner_radius=12,
        border_width=1,
        border_color=BORDER
    )

    overall.grid(
        row=1,
        column=0,
        sticky="ew",
        pady=(10, 0)
    )

    overall.grid_columnconfigure(
        0,
        weight=1
    )

    # ======================================================
    # Load Project
    # ======================================================

    def load_project(event=None):

        for widget in phases_frame.winfo_children():
            widget.destroy()

        for widget in overall.winfo_children():
            widget.destroy()

        selected_project = project_box.get()

        if not selected_project:
            return

        try:
            selected_index = project_values.index(
                selected_project
            )

        except ValueError:
            return

        project_id = projects[selected_index][0]

        # ==================================================
        # Project Dates
        # ==================================================

        project_dates = get_roadmap_project_dates(
            project_id
        )

        if project_dates:
            project_start = project_dates[0]
            project_end = project_dates[1]
        else:
            project_start = None
            project_end = None

        # ==================================================
        # Phases
        # ==================================================

        phases = get_roadmap_phases(
            project_id
        )

        # ==================================================
        # Overall Expected Price
        # Sum of all phase expected prices
        # ==================================================

        overall_expected = sum(
            float(phase[7] or 0)
            for phase in phases
        )

        # ==================================================
        # Overall Actual Price
        # Sum of all project expenses
        # ==================================================

        overall_actual = get_roadmap_project_actual_price(
            project_id
        )

        # ==================================================
        # Expected Overall Progress
        # ==================================================

        expected_overall = 0

        if not phases:

            ctk.CTkLabel(
                phases_frame,
                text="No phases assigned to this project.",
                font=FONT_NORMAL
            ).grid(
                row=0,
                column=0,
                pady=30
            )

        else:

            total_weight = 0
            weighted_expected = 0

            for phase_index, phase in enumerate(phases):

                project_phase_id = phase[0]
                phase_name = phase[1]
                weight = phase[2] or 0
                actual = phase[3] or 0
                status = phase[4]
                phase_start = phase[5]
                phase_end = phase[6]
                expected_price = phase[7] or 0

                # ------------------------------------------
                # Phase Date Fallback
                # ------------------------------------------

                if not phase_start:
                    phase_start = project_start

                if not phase_end:
                    phase_end = project_end

                # ------------------------------------------
                # Expected Progress
                # ------------------------------------------

                expected = calculate_expected_progress(
                    phase_start,
                    phase_end
                )

                try:
                    weight = float(weight)

                except (ValueError, TypeError):
                    weight = 0

                total_weight += weight

                weighted_expected += (
                        weight * expected
                )

                # ------------------------------------------
                # Actual Phase Price
                # ------------------------------------------

                actual_price = get_phase_actual_price(
                    project_phase_id
                )

                # ------------------------------------------
                # Create Phase
                # ------------------------------------------

                create_phase(
                    phases_frame,
                    phase_index,
                    phase_name,
                    actual,
                    expected,
                    status,
                    expected_price,
                    actual_price
                )

            if total_weight > 0:
                expected_overall = (
                        weighted_expected /
                        total_weight
                )

        # ==================================================
        # Overall Actual Progress
        # ==================================================

        actual_overall = get_roadmap_overall_actual(
            project_id
        )

        # ==================================================
        # Overall Header
        # ==================================================

        ctk.CTkLabel(
            overall,
            text="Overall Progress",
            font=("Segoe UI", 20, "bold")
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            padx=20,
            pady=(15, 10)
        )

        # ==================================================
        # Overall Main Content
        # ==================================================

        overall_content = ctk.CTkFrame(
            overall,
            fg_color="transparent"
        )

        overall_content.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=20,
            pady=(0, 15)
        )

        overall_content.grid_columnconfigure(
            0,
            weight=1
        )

        overall_content.grid_columnconfigure(
            1,
            weight=0
        )

        # ==================================================
        # Overall Progress
        # ==================================================

        progress_frame = ctk.CTkFrame(
            overall_content,
            fg_color="transparent"
        )

        progress_frame.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=5
        )

        progress_frame.grid_columnconfigure(
            1,
            weight=1
        )

        actual_color = get_actual_color(
            actual_overall,
            expected_overall
        )

        create_progress_bar(
            progress_frame,
            0,
            "Actual Progress",
            actual_overall,
            actual_color
        )

        create_progress_bar(
            progress_frame,
            1,
            "Expected Progress",
            expected_overall,
            EXPECTED_COLOR
        )

        # ==================================================
        # Overall Price
        # ==================================================

        create_price_bars(
            overall_content,
            0,
            1,
            overall_expected,
            overall_actual
        )


# ==========================================================
# Project Selection
# ==========================================================

    project_box.configure(
        command=load_project
    )

    # ======================================================
    # First Project
    # ======================================================

    if project_values:

        project_box.set(
            project_values[0]
        )

        load_project()


# ==========================================================
# Create Phase
# ==========================================================

def create_phase(
    parent,
    row,
    name,
    actual,
    expected,
    status,
    expected_price,
    actual_price
):

    frame = ctk.CTkFrame(
        parent,
        fg_color="transparent"
    )

    frame.grid(
        row=row,
        column=0,
        sticky="ew",
        padx=20,
        pady=15
    )

    frame.grid_columnconfigure(
        0,
        weight=1
    )

    frame.grid_columnconfigure(
        1,
        weight=0
    )

    current_row = frame.grid_size()[1]

    # ======================================================
    # Header
    # ======================================================

    header = ctk.CTkFrame(
        frame,
        fg_color="transparent"
    )

    header.grid(
        row=0,
        column=0,
        columnspan=2,
        sticky="ew"
    )

    header.grid_columnconfigure(
        0,
        weight=1
    )

    ctk.CTkLabel(
        header,
        text=f"Phase : {name}",
        font=("Segoe UI", 18, "bold")
    ).grid(
        row=0,
        column=0,
        sticky="w"
    )

    ctk.CTkLabel(
        header,
        text=status or "-",
        font=FONT_NORMAL
    ).grid(
        row=0,
        column=1,
        sticky="e",
        padx=10
    )

    # ======================================================
    # Progress Section
    # ======================================================

    progress_frame = ctk.CTkFrame(
        frame,
        fg_color="transparent"
    )

    progress_frame.grid(
        row=1,
        column=0,
        sticky="ew",
        pady=(8, 0)
    )

    progress_frame.grid_columnconfigure(
        1,
        weight=1
    )

    actual_color = get_actual_color(
        actual,
        expected
    )

    create_progress_bar(
        progress_frame,
        0,
        "Actual Progress",
        actual,
        actual_color
    )

    create_progress_bar(
        progress_frame,
        1,
        "Expected Progress",
        expected,
        EXPECTED_COLOR
    )

    # ======================================================
    # Price Section
    # ======================================================

    create_price_bars(
        frame,
        1,
        1,
        expected_price,
        actual_price
    )


# ==========================================================
# Create Progress Bar
# ==========================================================

def create_progress_bar(
    parent,
    row,
    title,
    value,
    color
):

    parent.grid_columnconfigure(
        1,
        weight=1
    )

    ctk.CTkLabel(
        parent,
        text=title,
        width=150,
        anchor="w",
        font=FONT_NORMAL
    ).grid(
        row=row,
        column=0,
        sticky="w",
        pady=5
    )

    bar = ctk.CTkProgressBar(
        parent,
        height=18
    )

    bar.grid(
        row=row,
        column=1,
        sticky="ew",
        padx=10,
        pady=5
    )

    try:
        value = float(value or 0)

    except (ValueError, TypeError):
        value = 0

    value = max(
        0,
        min(value, 100)
    )

    bar.set(
        value / 100
    )

    bar.configure(
        progress_color=color
    )

    ctk.CTkLabel(
        parent,
        text=f"{value:.0f}%",
        width=55,
        anchor="e",
        font=FONT_NORMAL
    ).grid(
        row=row,
        column=2,
        sticky="e",
        pady=5
    )