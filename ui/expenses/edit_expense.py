import customtkinter as ctk
from tkinter import messagebox
from persiantools.jdatetime import JalaliDate

from config import *
from db.lookups import get_values as get_lookup_values

from database import (
    get_expense_by_id,
    get_expense_projects,
    get_expense_phases,
    update_expense
)

from utils.jalali_calender import open_jalali_calendar
from utils.date_converter import (
    jalali_to_gregorian,
    gregorian_to_jalali
)


def open_edit_expense(parent, expense_id, on_saved=None):

    # ======================================================
    # Get Expense
    # ======================================================

    expense = get_expense_by_id(expense_id)

    if not expense:
        messagebox.showerror(
            "Error",
            "Expense not found.",
            parent=parent
        )
        return

    (
        db_expense_id,
        project_id,
        project_phase_id,
        title,
        expense_date,
        category,
        description,
        amount,
        paid_by,
        status
    ) = expense

    # ======================================================
    # Window
    # ======================================================

    window = ctk.CTkToplevel(parent)

    window.title("Edit Expense")
    window.geometry("600x760")
    window.minsize(500, 600)

    window.transient(parent)
    window.grab_set()

    # ======================================================
    # Main Container
    # ======================================================

    main_frame = ctk.CTkFrame(
        window,
        fg_color="transparent"
    )

    main_frame.pack(
        fill="both",
        expand=True
    )

    # ======================================================
    # Scrollable Form
    # ======================================================

    form = ctk.CTkScrollableFrame(
        main_frame,
        fg_color="transparent"
    )

    form.pack(
        fill="both",
        expand=True,
        padx=10,
        pady=(10, 0)
    )

    # ======================================================
    # Title
    # ======================================================

    ctk.CTkLabel(
        form,
        text="Title",
        font=FONT_NORMAL
    ).pack(
        anchor="w",
        padx=15,
        pady=(5, 5)
    )

    title_entry = ctk.CTkEntry(
        form,
        height=40
    )

    title_entry.pack(
        fill="x",
        padx=15,
        pady=(0, 15)
    )

    title_entry.insert(
        0,
        title or ""
    )

    # ======================================================
    # Project
    # ======================================================

    ctk.CTkLabel(
        form,
        text="Project",
        font=FONT_NORMAL
    ).pack(
        anchor="w",
        padx=15,
        pady=(5, 5)
    )

    projects = get_expense_projects()

    project_map = {
        name: project_id
        for project_id, name in projects
    }

    reverse_project_map = {
        project_id: name
        for project_id, name in projects
    }

    project_values = list(project_map.keys())

    project_menu = ctk.CTkComboBox(
        form,
        values=project_values,
        height=40
    )

    project_menu.pack(
        fill="x",
        padx=15,
        pady=(0, 15)
    )

    selected_project_name = reverse_project_map.get(
        project_id,
        ""
    )

    if selected_project_name:
        project_menu.set(selected_project_name)
    elif project_values:
        project_menu.set(project_values[0])



    # ======================================================
    # Phase
    # ======================================================

    ctk.CTkLabel(
        form,
        text="Phase",
        font=FONT_NORMAL
    ).pack(
        anchor="w",
        padx=15,
        pady=(5, 5)
    )

    phase_map = {}

    phase_menu = ctk.CTkComboBox(
        form,
        values=["No Phase"],
        height=40
    )

    phase_menu.pack(
        fill="x",
        padx=15,
        pady=(0, 15)
    )

    phase_menu.set("No Phase")

    def load_phases(selected_project=None):

        if selected_project is None:
            selected_project = project_menu.get()

        phase_map.clear()

        selected_id = project_map.get(
            selected_project
        )

        if not selected_id:
            phase_menu.configure(
                values=["No Phase"]
            )
            phase_menu.set("No Phase")
            return

        try:

            phases = get_expense_phases(
                selected_id
            )

        except Exception as e:

            messagebox.showerror(
                "Database Error",
                str(e),
                parent=window
            )

            phase_menu.configure(
                values=["No Phase"]
            )
            phase_menu.set("No Phase")
            return

        for phase_id, phase_name in phases:
            phase_map[phase_name] = phase_id

        phase_values = [
            "No Phase"
        ] + list(phase_map.keys())

        phase_menu.configure(
            values=phase_values
        )

        # ----------------------------------------------
        # Restore current phase
        # ----------------------------------------------

        current_phase_name = None

        for phase_name, phase_id in phase_map.items():

            if phase_id == project_phase_id:
                current_phase_name = phase_name
                break

        if current_phase_name:
            phase_menu.set(
                current_phase_name
            )
        else:
            phase_menu.set(
                "No Phase"
            )

    project_menu.configure(
        command=load_phases
    )

    # Load phases for current project
    load_phases()

    # ======================================================
    # Date
    # ======================================================

    ctk.CTkLabel(
        form,
        text="Date",
        font=FONT_NORMAL
    ).pack(
        anchor="w",
        padx=15,
        pady=(5, 5)
    )

    date_frame = ctk.CTkFrame(
        form,
        fg_color="transparent"
    )

    date_frame.pack(
        fill="x",
        padx=15,
        pady=(0, 15)
    )

    date_var = ctk.StringVar()

    date_entry = ctk.CTkEntry(
        date_frame,
        height=40,
        textvariable=date_var
    )

    date_entry.pack(
        side="left",
        fill="x",
        expand=True
    )

    # ------------------------------------------------------
    # Gregorian -> Jalali
    # ------------------------------------------------------

    if expense_date:

        try:
            jalali_date = gregorian_to_jalali(
                expense_date
            )

        except Exception:
            jalali_date = str(expense_date)

    else:

        today = JalaliDate.today()

        jalali_date = (
            f"{today.year:04d}/"
            f"{today.month:02d}/"
            f"{today.day:02d}"
        )

    date_var.set(
        jalali_date
    )

    calendar_button = ctk.CTkButton(
        date_frame,
        text="📅",
        width=50,
        height=40
    )

    calendar_button.pack(
        side="right",
        padx=(8, 0)
    )

    calendar_button.configure(
        command=lambda: open_jalali_calendar(
            window,
            date_var,
            calendar_button
        )
    )

    # ======================================================
    # Category
    # ======================================================

    ctk.CTkLabel(
        form,
        text="Category",
        font=FONT_NORMAL
    ).pack(
        anchor="w",
        padx=15,
        pady=(5, 5)
    )

    category_values = get_lookup_values("expense_category")

    category_menu = ctk.CTkComboBox(
        form,
        values=category_values,
        height=40
    )

    category_menu.pack(
        fill="x",
        padx=15,
        pady=(0, 15)
    )

    if category in category_values:
        category_menu.set(category)
    else:
        category_menu.set("Other")

    # ======================================================
    # Description
    # ======================================================

    ctk.CTkLabel(
        form,
        text="Description",
        font=FONT_NORMAL
    ).pack(
        anchor="w",
        padx=15,
        pady=(5, 5)
    )

    description_entry = ctk.CTkTextbox(
        form,
        height=100
    )

    description_entry.pack(
        fill="x",
        padx=15,
        pady=(0, 15)
    )

    description_entry.insert(
        "1.0",
        description or ""
    )

    # ======================================================
    # Amount
    # ======================================================

    ctk.CTkLabel(
        form,
        text="Amount (tomans)",
        font=FONT_NORMAL
    ).pack(
        anchor="w",
        padx=15,
        pady=(5, 5)
    )

    amount_entry = ctk.CTkEntry(
        form,
        height=40
    )

    amount_entry.pack(
        fill="x",
        padx=15,
        pady=(0, 15)
    )

    if amount is not None:

        try:
            amount_text = f"{float(amount):.2f}"

        except (ValueError, TypeError):
            amount_text = str(amount)

        amount_entry.insert(
            0,
            amount_text
        )

    # ======================================================
    # Paid By
    # ======================================================

    ctk.CTkLabel(
        form,
        text="Paid By",
        font=FONT_NORMAL
    ).pack(
        anchor="w",
        padx=15,
        pady=(5, 5)
    )

    paid_by_entry = ctk.CTkEntry(
        form,
        height=40
    )

    paid_by_entry.pack(
        fill="x",
        padx=15,
        pady=(0, 15)
    )

    paid_by_entry.insert(
        0,
        paid_by or ""
    )

    # ======================================================
    # Status
    # ======================================================

    ctk.CTkLabel(
        form,
        text="Status",
        font=FONT_NORMAL
    ).pack(
        anchor="w",
        padx=15,
        pady=(5, 5)
    )

    status_values = get_lookup_values("expense_status")

    status_menu = ctk.CTkComboBox(
        form,
        values=status_values,
        height=40
    )

    status_menu.pack(
        fill="x",
        padx=15,
        pady=(0, 20)
    )

    if status in status_values:
        status_menu.set(status)
    else:
        status_menu.set("Pending")

    # ======================================================
    # Save
    # ======================================================

    def save_changes():

        # --------------------------------------------------
        # Title
        # --------------------------------------------------

        expense_title = title_entry.get().strip()

        if not expense_title:

            messagebox.showerror(
                "Error",
                "Please enter an expense title.",
                parent=window
            )

            return

        # --------------------------------------------------
        # Project
        # --------------------------------------------------

        selected_project = project_menu.get().strip()

        new_project_id = project_map.get(
            selected_project
        )

        if not new_project_id:

            messagebox.showerror(
                "Error",
                "Please select a project.",
                parent=window
            )

            return

        # --------------------------------------------------
        # Phase
        # --------------------------------------------------

        selected_phase = phase_menu.get().strip()

        if selected_phase == "No Phase":

            new_project_phase_id = None

        else:

            new_project_phase_id = phase_map.get(
                selected_phase
            )

            if not new_project_phase_id:

                messagebox.showerror(
                    "Error",
                    "Invalid phase selection.",
                    parent=window
                )

                return

        # --------------------------------------------------
        # Date
        # --------------------------------------------------

        jalali_date = date_var.get().strip()

        if not jalali_date:

            messagebox.showerror(
                "Error",
                "Please enter a date.",
                parent=window
            )

            return

        try:

            new_date = jalali_to_gregorian(
                jalali_date
            )

        except Exception:

            messagebox.showerror(
                "Error",
                "Invalid date format.",
                parent=window
            )

            return

        # --------------------------------------------------
        # Amount
        # --------------------------------------------------

        amount_text = amount_entry.get().strip()

        if not amount_text:

            messagebox.showerror(
                "Error",
                "Please enter an amount.",
                parent=window
            )

            return

        try:

            new_amount = float(
                amount_text.replace(",", "")
            )

        except ValueError:

            messagebox.showerror(
                "Error",
                "Please enter a valid amount.",
                parent=window
            )

            return

        if new_amount <= 0:

            messagebox.showerror(
                "Error",
                "Amount must be greater than zero.",
                parent=window
            )

            return

        # --------------------------------------------------
        # Category
        # --------------------------------------------------

        new_category = category_menu.get()

        if not new_category:

            messagebox.showerror(
                "Error",
                "Please select a category.",
                parent=window
            )

            return

        # --------------------------------------------------
        # Description
        # --------------------------------------------------

        new_description = (
            description_entry
            .get(
                "1.0",
                "end-1c"
            )
            .strip()
        )

        # --------------------------------------------------
        # Paid By
        # --------------------------------------------------

        new_paid_by = (
            paid_by_entry
            .get()
            .strip()
        )

        # --------------------------------------------------
        # Status
        # --------------------------------------------------

        new_status = status_menu.get()

        # ==================================================
        # Update Database
        # ==================================================

        try:

            update_expense(
                expense_id=db_expense_id,
                project_id=new_project_id,
                project_phase_id=new_project_phase_id,
                title=expense_title,
                expense_date=new_date,
                category=new_category,
                description=new_description,
                amount=new_amount,
                paid_by=new_paid_by,
                status=new_status
            )

        except Exception as e:

            messagebox.showerror(
                "Database Error",
                str(e),
                parent=window
            )

            return

        # ==================================================
        # Refresh
        # ==================================================

        if on_saved:
            on_saved()

        messagebox.showinfo(
            "Success",
            "Expense updated successfully.",
            parent=window
        )

        window.destroy()

    # ======================================================
    # Bottom Buttons
    # ======================================================

    button_frame = ctk.CTkFrame(
        main_frame,
        fg_color="transparent"
    )

    button_frame.pack(
        fill="x",
        padx=15,
        pady=15
    )

    save_button = ctk.CTkButton(
        button_frame,
        text="Save Changes",
        height=42,
        command=save_changes
    )

    save_button.pack(
        side="left",
        expand=True,
        fill="x",
        padx=(0, 5)
    )

    cancel_button = ctk.CTkButton(
        button_frame,
        text="Cancel",
        height=42,
        fg_color="gray",
        hover_color="darkgray",
        command=window.destroy
    )

    cancel_button.pack(
        side="left",
        expand=True,
        fill="x",
        padx=(5, 0)
    )

    # ======================================================
    # Keyboard
    # ======================================================

    window.bind(
        "<Escape>",
        lambda event: window.destroy()
    )

    title_entry.focus()