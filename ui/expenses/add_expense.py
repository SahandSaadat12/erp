import customtkinter as ctk
from tkinter import messagebox
from persiantools.jdatetime import JalaliDate

from config import *
from db.lookups import get_values as get_lookup_values

from database import (
    insert_expense,
    get_expense_projects,
    get_expense_phases
)

from utils.jalali_calender import open_jalali_calendar
from utils.date_converter import jalali_to_gregorian


def open_add_expense(parent, on_saved=None):

    window = ctk.CTkToplevel(parent)

    window.title("Add Expense")
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
        height=40,
        placeholder_text="Expense title"
    )

    title_entry.pack(
        fill="x",
        padx=15,
        pady=(0, 15)
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


    project_menu = ctk.CTkComboBox(
        form,
        values=list(project_map.keys()),
        height=40
    )

    project_menu.pack(
        fill="x",
        padx=15,
        pady=(0, 15)
    )


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


    def load_phases(*args):

        selected_project = project_menu.get()

        phase_map.clear()

        if not selected_project:
            phase_menu.configure(
                values=["No Phase"]
            )
            phase_menu.set("No Phase")
            return


        project_id = project_map.get(
            selected_project
        )

        if not project_id:
            phase_menu.configure(
                values=["No Phase"]
            )
            phase_menu.set("No Phase")
            return


        try:

            phases = get_expense_phases(
                project_id
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

        phase_menu.set(
            "No Phase"
        )


    project_menu.configure(
        command=load_phases
    )


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


    today = JalaliDate.today()

    jalali_today = (
        f"{today.year:04d}/"
        f"{today.month:02d}/"
        f"{today.day:02d}"
    )

    date_var.set(
        jalali_today
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


    category_menu = ctk.CTkComboBox(
        form,
        values=get_lookup_values("expense_category"),
        height=40
    )

    category_menu.pack(
        fill="x",
        padx=15,
        pady=(0, 15)
    )

    category_menu.set(
        "Materials"
    )


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
        height=40,
        placeholder_text="0.00"
    )

    amount_entry.pack(
        fill="x",
        padx=15,
        pady=(0, 15)
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
        height=40,
        placeholder_text="Person who paid"
    )

    paid_by_entry.pack(
        fill="x",
        padx=15,
        pady=(0, 15)
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


    status_menu = ctk.CTkComboBox(
        form,
        values=get_lookup_values("expense_status"),
        height=40
    )

    status_menu.pack(
        fill="x",
        padx=15,
        pady=(0, 20)
    )

    status_menu.set(
        "Pending"
    )


    # ======================================================
    # Save
    # ======================================================

    def save_expense():

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

        if not selected_project:

            messagebox.showerror(
                "Error",
                "Please select a project.",
                parent=window
            )

            return


        project_id = project_map.get(
            selected_project
        )

        if not project_id:

            messagebox.showerror(
                "Error",
                "Invalid project selection.",
                parent=window
            )

            return


        # --------------------------------------------------
        # Phase
        # --------------------------------------------------

        selected_phase = phase_menu.get().strip()

        if selected_phase == "No Phase":

            project_phase_id = None

        else:

            project_phase_id = phase_map.get(
                selected_phase
            )

            if not project_phase_id:

                messagebox.showerror(
                    "Error",
                    "Invalid phase selection.",
                    parent=window
                )

                return


        # --------------------------------------------------
        # Convert Jalali -> Gregorian
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

            expense_date = jalali_to_gregorian(
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

            expense_amount = float(
                amount_text.replace(",", "")
            )

        except ValueError:

            messagebox.showerror(
                "Error",
                "Please enter a valid amount.",
                parent=window
            )

            return


        if expense_amount <= 0:

            messagebox.showerror(
                "Error",
                "Amount must be greater than zero.",
                parent=window
            )

            return


        # --------------------------------------------------
        # Description
        # --------------------------------------------------

        description = (
            description_entry
            .get(
                "1.0",
                "end-1c"
            )
            .strip()
        )


        # --------------------------------------------------
        # Paid By / Status
        # --------------------------------------------------

        paid_by = paid_by_entry.get().strip()

        selected_status = status_menu.get()


        # --------------------------------------------------
        # Insert
        # --------------------------------------------------

        try:

            insert_expense(
                project_id=project_id,
                project_phase_id=project_phase_id,
                title=expense_title,
                expense_date=expense_date,
                category=category_menu.get(),
                description=description,
                amount=expense_amount,
                paid_by=paid_by,
                status=selected_status
            )

        except Exception as e:

            messagebox.showerror(
                "Database Error",
                str(e),
                parent=window
            )

            return


        # --------------------------------------------------
        # Refresh
        # --------------------------------------------------

        if on_saved:
            on_saved()


        messagebox.showinfo(
            "Success",
            "Expense added successfully.",
            parent=window
        )


        window.destroy()


    # ======================================================
    # Buttons
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
        text="Save Expense",
        height=42,
        command=save_expense
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
    # Escape
    # ======================================================

    window.bind(
        "<Escape>",
        lambda event: window.destroy()
    )


    title_entry.focus()