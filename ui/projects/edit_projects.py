import customtkinter as ctk
from tkinter import messagebox

from config import *
from db.lookups import get_values as get_lookup_values

from utils.jalali_calender import open_jalali_calendar
from utils.date_converter import (
    jalali_to_gregorian,
    gregorian_to_jalali
)


def edit_project(database, tree):

    # ==========================================================
    # Selected Project
    # ==========================================================

    selected = tree.selection()

    if not selected:

        messagebox.showwarning(
            "No Selection",
            "Please select a project first."
        )

        return

    item = tree.item(
        selected[0]
    )

    values = item.get("values")

    if not values:

        messagebox.showerror(
            "Error",
            "Invalid project data."
        )

        return

    project_code = values[0]

    # ==========================================================
    # Get Project
    # ==========================================================

    project = database.get_project_details(
        project_code
    )

    if not project:

        messagebox.showerror(
            "Error",
            "Project not found."
        )

        return

    project_id = project[0]

    # ==========================================================
    # Window
    # ==========================================================

    window = ctk.CTkToplevel()

    window.title(
        "Edit Project"
    )

    window.geometry(
        "1000x750"
    )

    window.minsize(
        900,
        700
    )

    window.grab_set()

    # ==========================================================
    # Main Frame
    # ==========================================================

    main_frame = ctk.CTkScrollableFrame(
        window,
        fg_color="transparent"
    )

    main_frame.pack(
        fill="both",
        expand=True,
        padx=15,
        pady=15
    )

    # ==========================================================
    # Project Information
    # ==========================================================

    info_frame = ctk.CTkFrame(
        main_frame,
        fg_color=CARD,
        corner_radius=12,
        border_width=1,
        border_color=BORDER
    )

    info_frame.pack(
        fill="x",
        pady=(0, 15)
    )

    ctk.CTkLabel(
        info_frame,
        text="Project Information",
        font=FONT_TITLE
    ).grid(
        row=0,
        column=0,
        columnspan=2,
        padx=15,
        pady=15,
        sticky="w"
    )

    # ==========================================================
    # Project Code
    # ==========================================================

    project_code_entry = ctk.CTkEntry(
        info_frame,
        placeholder_text="Project Code"
    )

    project_code_entry.grid(
        row=1,
        column=0,
        padx=15,
        pady=10,
        sticky="ew"
    )

    project_code_entry.insert(
        0,
        project[1] or ""
    )

    # ==========================================================
    # Project Name
    # ==========================================================

    project_name_entry = ctk.CTkEntry(
        info_frame,
        placeholder_text="Project Name"
    )

    project_name_entry.grid(
        row=1,
        column=1,
        padx=15,
        pady=10,
        sticky="ew"
    )

    project_name_entry.insert(
        0,
        project[2] or ""
    )

    # ==========================================================
    # Expected Price
    # ==========================================================

    expected_price_entry = ctk.CTkEntry(
        info_frame,
        placeholder_text="Expected Price"
    )

    expected_price_entry.grid(
        row=2,
        column=0,
        padx=15,
        pady=10,
        sticky="ew"
    )

    expected_price_entry.insert(
        0,
        str(project[12] or 0)
    )

    # ==========================================================
    # Client
    # ==========================================================

    clients = database.get_clients()

    client_map = {
        client[1]: client[0]
        for client in clients
    }

    client_combo = ctk.CTkComboBox(
        info_frame,
        values=list(client_map.keys())
    )

    client_combo.grid(
        row=2,
        column=1,
        padx=15,
        pady=10,
        sticky="ew"
    )

    client_combo.set(
        project[3] or ""
    )

    # ==========================================================
    # Project Type
    # ==========================================================

    type_combo = ctk.CTkComboBox(
        info_frame,
        values=get_lookup_values("project_type")
    )

    type_combo.grid(
        row=3,
        column=0,
        padx=15,
        pady=10,
        sticky="ew"
    )

    type_combo.set(
        project[4] or ""
    )

    # ==========================================================
    # Department
    # ==========================================================

    departments = database.get_departments()

    department_map = {
        department[1]: department[0]
        for department in departments
    }

    department_combo = ctk.CTkComboBox(
        info_frame,
        values=list(department_map.keys())
    )

    department_combo.grid(
        row=3,
        column=1,
        padx=15,
        pady=10,
        sticky="ew"
    )

    department_combo.set(
        project[5] or ""
    )

    # ==========================================================
    # Manager
    # ==========================================================

    managers = database.get_managers()

    manager_map = {
        manager[1]: manager[0]
        for manager in managers
    }

    manager_combo = ctk.CTkComboBox(
        info_frame,
        values=list(manager_map.keys())
    )

    manager_combo.grid(
        row=4,
        column=0,
        padx=15,
        pady=10,
        sticky="ew"
    )

    manager_combo.set(
        project[6] or ""
    )

    # ==========================================================
    # Priority
    # ==========================================================

    priority_combo = ctk.CTkComboBox(
        info_frame,
        values=get_lookup_values("priority")
    )

    priority_combo.grid(
        row=4,
        column=1,
        padx=15,
        pady=10,
        sticky="ew"
    )

    priority_combo.set(
        project[9] or ""
    )

    # ==========================================================
    # Status
    # ==========================================================

    status_combo = ctk.CTkComboBox(
        info_frame,
        values=get_lookup_values("project_status")
    )

    status_combo.grid(
        row=5,
        column=0,
        padx=15,
        pady=10,
        sticky="ew"
    )

    status_combo.set(
        project[10] or ""
    )

    # ==========================================================
    # Start Date
    # ==========================================================

    start_date_var = ctk.StringVar()

    start_date_entry = ctk.CTkEntry(
        info_frame,
        textvariable=start_date_var,
        placeholder_text="Start Date"
    )

    start_date_entry.grid(
        row=5,
        column=1,
        padx=15,
        pady=10,
        sticky="ew"
    )

    if project[7]:

        start_date_var.set(
            gregorian_to_jalali(
                project[7]
            )
        )

    start_date_button = ctk.CTkButton(
        info_frame,
        text="📅",
        width=45
    )

    start_date_button.configure(
        command=lambda:
        open_jalali_calendar(
            window,
            start_date_var,
            start_date_button
        )
    )

    start_date_button.grid(
        row=5,
        column=1,
        padx=(0, 15),
        pady=10,
        sticky="e"
    )

    # ==========================================================
    # End Date
    # ==========================================================

    end_date_var = ctk.StringVar()

    end_date_entry = ctk.CTkEntry(
        info_frame,
        textvariable=end_date_var,
        placeholder_text="End Date"
    )

    end_date_entry.grid(
        row=6,
        column=0,
        padx=15,
        pady=10,
        sticky="ew"
    )

    if project[8]:

        end_date_var.set(
            gregorian_to_jalali(
                project[8]
            )
        )

    end_date_button = ctk.CTkButton(
        info_frame,
        text="📅",
        width=45
    )

    end_date_button.configure(
        command=lambda:
        open_jalali_calendar(
            window,
            end_date_var,
            end_date_button
        )
    )

    end_date_button.grid(
        row=6,
        column=0,
        padx=(0, 15),
        pady=10,
        sticky="e"
    )

    info_frame.grid_columnconfigure(
        0,
        weight=1
    )

    info_frame.grid_columnconfigure(
        1,
        weight=1
    )

    # ==========================================================
    # Project Phases
    # ==========================================================

    phases_frame = ctk.CTkFrame(
        main_frame,
        fg_color=CARD,
        corner_radius=12,
        border_width=1,
        border_color=BORDER
    )

    phases_frame.pack(
        fill="x",
        pady=(0, 15)
    )

    ctk.CTkLabel(
        phases_frame,
        text="Project Phases",
        font=FONT_TITLE
    ).grid(
        row=0,
        column=0,
        columnspan=6,
        padx=15,
        pady=15,
        sticky="w"
    )

    # ==========================================================
    # Phase Headers
    # ==========================================================

    headers = [
        ("Phase", 0),
        ("Weight (%)", 1),
        ("Expected Price", 2),
        ("Progress (%)", 3),
        ("Start Date", 4),
        ("End Date", 5)
    ]

    for text, column in headers:

        ctk.CTkLabel(
            phases_frame,
            text=text
        ).grid(
            row=1,
            column=column,
            padx=10,
            pady=5
        )

    phase_entries = []

    # ==========================================================
    # Load Project Phases
    # ==========================================================

    def load_project_phases(project_id):

        for widget in phases_frame.winfo_children():

            grid_info = widget.grid_info()

            if "row" in grid_info:

                if int(grid_info["row"]) > 1:

                    widget.destroy()

        phase_entries.clear()

        phases = database.get_project_phases(
            project_id
        )

        for index, phase in enumerate(phases):

            row = index + 2

            # ==================================================
            # Phase Name
            # ==================================================

            ctk.CTkLabel(
                phases_frame,
                text=phase[1]
            ).grid(
                row=row,
                column=0,
                padx=10,
                pady=5,
                sticky="w"
            )

            # ==================================================
            # Weight
            # ==================================================

            weight_entry = ctk.CTkEntry(
                phases_frame,
                width=90
            )

            weight_entry.insert(
                0,
                phase[2]
            )

            weight_entry.grid(
                row=row,
                column=1,
                padx=10,
                pady=5
            )

            # ==================================================
            # Expected Price
            # ==================================================

            expected_price_entry = ctk.CTkEntry(
                phases_frame,
                width=120
            )

            expected_price_entry.insert(
                0,
                str(phase[6] or 0)
            )

            expected_price_entry.grid(
                row=row,
                column=2,
                padx=10,
                pady=5
            )

            # ==================================================
            # Progress
            # ==================================================

            progress_entry = ctk.CTkEntry(
                phases_frame,
                fg_color=BLUE,
                border_color=BLUE,
                text_color=TEXT,
                width=90
            )

            progress_entry.insert(
                0,
                phase[3] or 0
            )

            progress_entry.grid(
                row=row,
                column=3,
                padx=10,
                pady=5
            )

            # ==================================================
            # Start Date
            # ==================================================

            phase_start_var = ctk.StringVar()

            start_date_entry = ctk.CTkEntry(
                phases_frame,
                width=130,
                textvariable=phase_start_var,
                placeholder_text="Start Date"
            )

            start_date_entry.grid(
                row=row,
                column=4,
                padx=(10, 2),
                pady=5
            )

            if phase[4]:

                phase_start_var.set(
                    gregorian_to_jalali(
                        phase[4]
                    )
                )

            start_date_button = ctk.CTkButton(
                phases_frame,
                text="📅",
                width=35
            )

            start_date_button.configure(
                command=lambda
                    var=phase_start_var,
                    button=start_date_button:
                    open_jalali_calendar(
                        window,
                        var,
                        button
                    )
            )

            start_date_button.grid(
                row=row,
                column=4,
                padx=(0, 10),
                pady=5,
                sticky="e"
            )

            # ==================================================
            # End Date
            # ==================================================

            phase_end_var = ctk.StringVar()

            end_date_entry = ctk.CTkEntry(
                phases_frame,
                width=130,
                textvariable=phase_end_var,
                placeholder_text="End Date"
            )

            end_date_entry.grid(
                row=row,
                column=5,
                padx=(10, 2),
                pady=5
            )

            if phase[5]:

                phase_end_var.set(
                    gregorian_to_jalali(
                        phase[5]
                    )
                )

            end_date_button = ctk.CTkButton(
                phases_frame,
                text="📅",
                width=35
            )

            end_date_button.configure(
                command=lambda
                    var=phase_end_var,
                    button=end_date_button:
                    open_jalali_calendar(
                        window,
                        var,
                        button
                    )
            )

            end_date_button.grid(
                row=row,
                column=5,
                padx=(0, 10),
                pady=5,
                sticky="e"
            )

            # ==================================================
            # Store
            # ==================================================

            phase_entries.append(
                (
                    phase[0],
                    weight_entry,
                    expected_price_entry,
                    progress_entry,
                    phase_start_var,
                    phase_end_var
                )
            )

    # ==========================================================
    # Load Existing Phases
    # ==========================================================

    load_project_phases(
        project_id
    )

    # ==========================================================
    # Description
    # ==========================================================

    description_frame = ctk.CTkFrame(
        main_frame,
        fg_color=CARD,
        corner_radius=12,
        border_width=1,
        border_color=BORDER
    )

    description_frame.pack(
        fill="x",
        pady=(0, 15)
    )

    ctk.CTkLabel(
        description_frame,
        text="Description",
        font=FONT_TITLE
    ).pack(
        anchor="w",
        padx=15,
        pady=(15, 10)
    )

    description_box = ctk.CTkTextbox(
        description_frame,
        height=120
    )

    description_box.pack(
        fill="x",
        padx=15,
        pady=(0, 15)
    )

    description_box.insert(
        "1.0",
        project[11] or ""
    )

    # ==========================================================
    # Save Changes
    # ==========================================================

    def save_changes():

        new_project_code = (
            project_code_entry.get().strip()
        )

        new_project_name = (
            project_name_entry.get().strip()
        )

        # ======================================================
        # Basic Validation
        # ======================================================

        if not new_project_code:

            messagebox.showwarning(
                "Validation",
                "Project code cannot be empty."
            )

            return

        if not new_project_name:

            messagebox.showwarning(
                "Validation",
                "Project name cannot be empty."
            )

            return

        # ======================================================
        # Expected Price
        # ======================================================

        try:

            expected_price = float(
                expected_price_entry.get().strip() or 0
            )

            if expected_price < 0:

                messagebox.showwarning(
                    "Invalid Expected Price",
                    "Expected price cannot be negative."
                )

                return

        except ValueError:

            messagebox.showwarning(
                "Invalid Expected Price",
                "Expected price must be a valid number."
            )

            return

        # ======================================================
        # Project Dates
        # ======================================================

        project_start = (
            start_date_var.get().strip()
        )

        project_end = (
            end_date_var.get().strip()
        )

        if not project_start or not project_end:

            messagebox.showwarning(
                "Invalid Dates",
                "Project Start Date and End Date are required."
            )

            return

        try:

            project_start_gregorian = (
                jalali_to_gregorian(
                    project_start
                )
            )

            project_end_gregorian = (
                jalali_to_gregorian(
                    project_end
                )
            )

        except Exception:

            messagebox.showwarning(
                "Invalid Dates",
                "Project dates are invalid."
            )

            return

        if project_start_gregorian > project_end_gregorian:

            messagebox.showwarning(
                "Invalid Dates",
                "Project start date cannot be after "
                "the project end date."
            )

            return

        # ======================================================
        # Validate Phases
        # ======================================================

        total_weight = 0

        phase_data = []

        try:

            for (
                phase_id,
                weight_entry,
                phase_expected_entry,
                progress_entry,
                phase_start_var,
                phase_end_var
            ) in phase_entries:

                # ==================================================
                # Weight
                # ==================================================

                weight = float(
                    weight_entry.get().strip()
                )

                if weight < 0 or weight > 100:

                    messagebox.showwarning(
                        "Invalid Weight",
                        "Phase weight must be between 0 and 100."
                    )

                    return

                total_weight += weight

                # ==================================================
                # Expected Price
                # ==================================================

                phase_expected_price = float(
                    phase_expected_entry.get().strip() or 0
                )

                if phase_expected_price < 0:

                    messagebox.showwarning(
                        "Invalid Expected Price",
                        "Phase expected price cannot be negative."
                    )

                    return

                # ==================================================
                # Progress
                # ==================================================

                progress = float(
                    progress_entry.get().strip()
                )

                if progress < 0 or progress > 100:

                    messagebox.showwarning(
                        "Invalid Progress",
                        "Phase progress must be between 0 and 100."
                    )

                    return

                # ==================================================
                # Phase Dates
                # ==================================================

                phase_start = (
                    phase_start_var.get().strip()
                )

                phase_end = (
                    phase_end_var.get().strip()
                )

                if not phase_start and not phase_end:

                    phase_start_gregorian = None
                    phase_end_gregorian = None

                elif not phase_start or not phase_end:

                    messagebox.showwarning(
                        "Invalid Phase Dates",
                        "Please enter both Start Date and End Date "
                        "for a phase, or leave both empty."
                    )

                    return

                else:

                    phase_start_gregorian = (
                        jalali_to_gregorian(
                            phase_start
                        )
                    )

                    phase_end_gregorian = (
                        jalali_to_gregorian(
                            phase_end
                        )
                    )

                    if phase_start_gregorian > phase_end_gregorian:

                        messagebox.showwarning(
                            "Invalid Phase Dates",
                            "Phase start date cannot be after "
                            "the phase end date."
                        )

                        return

                    if phase_start_gregorian < project_start_gregorian:

                        messagebox.showwarning(
                            "Invalid Phase Dates",
                            "Phase start date cannot be before "
                            "the project start date."
                        )

                        return

                    if phase_end_gregorian > project_end_gregorian:

                        messagebox.showwarning(
                            "Invalid Phase Dates",
                            "Phase end date cannot be after "
                            "the project end date."
                        )

                        return

                phase_data.append(
                    (
                        phase_id,
                        weight,
                        phase_expected_price,
                        progress,
                        phase_start_gregorian,
                        phase_end_gregorian
                    )
                )

        except ValueError:

            messagebox.showerror(
                "Invalid Value",
                "Weight, Expected Price and Progress "
                "must be valid numbers."
            )

            return

        except Exception as error:

            messagebox.showerror(
                "Invalid Date",
                f"Invalid phase date:\n\n{error}"
            )

            return

        # ======================================================
        # Validate Total Weight
        # ======================================================

        if phase_entries:

            if abs(total_weight - 100) > 0.001:

                messagebox.showwarning(
                    "Invalid Weights",
                    f"Total phase weight must be 100%.\n\n"
                    f"Current total: {total_weight:g}%"
                )

                return

        # ======================================================
        # Update Database
        # ======================================================

        try:

            # ==================================================
            # Update Project
            # ==================================================

            database.update_project(

                project_id,

                new_project_code,

                new_project_name,

                client_map.get(
                    client_combo.get()
                ),

                type_combo.get(),

                department_map.get(
                    department_combo.get()
                ),

                manager_map.get(
                    manager_combo.get()
                ),

                project_start_gregorian,

                project_end_gregorian,

                priority_combo.get(),

                status_combo.get(),

                description_box.get(
                    "1.0",
                    "end"
                ).strip(),

                expected_price
            )

            # ==================================================
            # Update Phases
            # ==================================================

            for (
                phase_id,
                weight,
                phase_expected_price,
                progress,
                phase_start_gregorian,
                phase_end_gregorian
            ) in phase_data:

                database.update_project_phase(

                    phase_id,

                    weight,

                    progress,

                    phase_start_gregorian,

                    phase_end_gregorian,

                    phase_expected_price
                )

            # ==================================================
            # Success
            # ==================================================

            messagebox.showinfo(
                "Success",
                "Project updated successfully."
            )

            window.destroy()

        except Exception as error:

            messagebox.showerror(
                "Update Error",
                f"Failed to update project:\n\n{error}"
            )

    # ==========================================================
    # Save Button
    # ==========================================================

    save_button = ctk.CTkButton(
        main_frame,
        text="💾 Save Changes",
        width=180,
        fg_color=GREEN,
        hover_color=GREEN_HOVER,
        command=save_changes
    )

    save_button.pack(
        pady=(30, 30)
    )