import customtkinter as ctk
from tkinter import messagebox

from config import *
from db.lookups import get_values as get_lookup_values
from db.projects import DuplicateProjectCodeError


from utils.jalali_calender import open_jalali_calendar
from utils.date_converter import jalali_to_gregorian, InvalidDateError

def add_project(database):

    window = ctk.CTkToplevel()

    window.title("Add Project")
    window.geometry("900x700")
    window.minsize(800, 650)

    window.grab_set()

    # =====================================
    # Main Scrollable Frame
    # =====================================

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

    # =====================================
    # Title
    # =====================================

    title = ctk.CTkLabel(
        main_frame,
        text="Add New Project",
        font=FONT_TITLE
    )

    title.pack(
        anchor="w",
        pady=(0, 15)
    )

    # =====================================
    # Project Information
    # =====================================

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

    info_frame.grid_columnconfigure(
        (0, 1),
        weight=1
    )

    section_title = ctk.CTkLabel(
        info_frame,
        text="Project Information",
        font=FONT_TITLE
    )

    section_title.grid(
        row=0,
        column=0,
        columnspan=2,
        sticky="w",
        padx=15,
        pady=(15, 10)
    )

    # =====================================
    # Project Code
    # =====================================

    project_code = ctk.CTkEntry(
        info_frame,
        placeholder_text="Project Code"
    )

    project_code.grid(
        row=1,
        column=0,
        sticky="ew",
        padx=15,
        pady=5
    )

    # =====================================
    # Project Name
    # =====================================

    project_name = ctk.CTkEntry(
        info_frame,
        placeholder_text="Project Name"
    )

    project_name.grid(
        row=1,
        column=1,
        sticky="ew",
        padx=15,
        pady=5
    )

    # =====================================
    # Client
    # =====================================

    clients = database.get_clients()

    client_map = {
        client[1]: client[0]
        for client in clients
    }

    client_combo = ctk.CTkComboBox(
        info_frame,
        values=list(client_map.keys())
    )

    client_combo.set(
        "Select Client"
    )

    client_combo.grid(
        row=2,
        column=0,
        sticky="ew",
        padx=15,
        pady=5
    )

    # =====================================
    # Project Type
    # =====================================

    type_combo = ctk.CTkComboBox(
        info_frame,
        values=get_lookup_values("project_type")
    )

    type_combo.set(
        "Engineering"
    )

    type_combo.grid(
        row=2,
        column=1,
        sticky="ew",
        padx=15,
        pady=5
    )

    # =====================================
    # Department
    # =====================================

    departments = database.get_departments()

    department_map = {
        department[1]: department[0]
        for department in departments
    }

    department_combo = ctk.CTkComboBox(
        info_frame,
        values=list(department_map.keys())
    )

    department_combo.set(
        "Select Department"
    )

    department_combo.grid(
        row=3,
        column=0,
        sticky="ew",
        padx=15,
        pady=5
    )

    # =====================================
    # Manager
    # =====================================

    managers = database.get_managers()

    manager_map = {
        manager[1]: manager[0]
        for manager in managers
    }

    manager_combo = ctk.CTkComboBox(
        info_frame,
        values=list(manager_map.keys())
    )

    manager_combo.set(
        "Select Manager"
    )

    manager_combo.grid(
        row=3,
        column=1,
        sticky="ew",
        padx=15,
        pady=5
    )

    # =====================================
    # Priority
    # =====================================

    priority_combo = ctk.CTkComboBox(
        info_frame,
        values=get_lookup_values("priority")
    )

    priority_combo.set(
        "Medium"
    )

    priority_combo.grid(
        row=4,
        column=0,
        sticky="ew",
        padx=15,
        pady=5
    )

    # =====================================
    # Status
    # =====================================

    status_combo = ctk.CTkComboBox(
        info_frame,
        values=get_lookup_values("project_status")
    )

    status_combo.set(
        "Open"
    )

    status_combo.grid(
        row=4,
        column=1,
        sticky="ew",
        padx=15,
        pady=5
    )

    # =====================================
    # Start Date
    # =====================================

    start_date = ctk.StringVar()


    def open_start_calendar():

        open_jalali_calendar(
            window,
            start_date,
            start_date_button
        )

    start_date_button = ctk.CTkButton(
        info_frame,
        text="📅 Start Date",
        command=open_start_calendar
    )

    start_date_button.grid(
        row=5,
        column=0,
        sticky="ew",
        padx=15,
        pady=5
    )



    # =====================================
    # End Date
    # =====================================

    end_date = ctk.StringVar()

    def open_end_calendar():

        open_jalali_calendar(
            window,
            end_date,
            end_date_button
        )

    end_date_button = ctk.CTkButton(
        info_frame,
        text="📅 End Date",
        command=open_end_calendar
    )

    end_date_button.grid(
        row=5,
        column=1,
        sticky="ew",
        padx=15,
        pady=(5, 15)
    )

    # =====================================
    # Project Phases
    # =====================================

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

    phases_frame.grid_columnconfigure(
        1,
        weight=1
    )

    phase_title = ctk.CTkLabel(
        phases_frame,
        text="Project Phases",
        font=FONT_TITLE
    )

    phase_title.grid(
        row=0,
        column=0,
        columnspan=3,
        sticky="w",
        padx=15,
        pady=(15, 10)
    )

    ctk.CTkLabel(
        phases_frame,
        text="Select",
        font=("Segoe UI", 13)
    ).grid(
        row=1,
        column=0,
        padx=15,
        pady=5
    )

    ctk.CTkLabel(
        phases_frame,
        text="Phase",
        font=("Segoe UI", 13)
    ).grid(
        row=1,
        column=1,
        sticky="w",
        padx=10,
        pady=5
    )

    ctk.CTkLabel(
        phases_frame,
        text="Weight (%)",
        font=("Segoe UI", 13)
    ).grid(
        row=1,
        column=2,
        padx=15,
        pady=5
    )

    # =====================================
    # Phases
    # =====================================

    default_phases = database.get_phases()

    phase_widgets = []

    def update_total():

        total = 0

        for checkbox, entry, phase_id in phase_widgets:

            if checkbox.get() == 1:

                try:
                    total += float(
                        entry.get()
                    )

                except (ValueError, TypeError):
                    pass

        total_label.configure(
            text=f"Total Weight : {total}%"
        )

        if total == 100:

            total_label.configure(
                text_color=GREEN
            )

        else:

            total_label.configure(
                text_color=RED
            )

    def refresh_phases():

        for widget in phases_frame.winfo_children():

            if int(widget.grid_info()["row"]) > 1:
                widget.destroy()

        phase_widgets.clear()

        phases = database.get_phases()

        for index, phase in enumerate(phases):

            row = index + 2

            checkbox = ctk.CTkCheckBox(
                phases_frame,
                text=""
            )

            checkbox.grid(
                row=row,
                column=0,
                padx=15,
                pady=5
            )

            phase_label = ctk.CTkLabel(
                phases_frame,
                text=phase[1],
                font=("Segoe UI", 13)
            )

            phase_label.grid(
                row=row,
                column=1,
                sticky="w",
                padx=10,
                pady=5
            )

            percentage_entry = ctk.CTkEntry(
                phases_frame,
                width=100,
                placeholder_text="%"
            )

            percentage_entry.grid(
                row=row,
                column=2,
                padx=15,
                pady=5
            )

            percentage_entry.configure(
                state="disabled"
            )

            def toggle_phase(
                entry=percentage_entry,
                checkbox=checkbox
            ):

                if checkbox.get() == 1:

                    entry.configure(
                        state="normal"
                    )

                else:

                    entry.delete(
                        0,
                        "end"
                    )

                    entry.configure(
                        state="disabled"
                    )

                update_total()

            checkbox.configure(
                command=toggle_phase
            )

            percentage_entry.bind(
                "<KeyRelease>",
                lambda event: update_total()
            )

            phase_widgets.append(
                (
                    checkbox,
                    percentage_entry,
                    phase[0]
                )
            )

        total_label.configure(
            text="Total Weight : 0%"
        )

    def add_new_phase():

        phase_window = ctk.CTkToplevel()

        phase_window.title("Add Phase")
        phase_window.geometry("400x200")

        phase_window.grab_set()

        phase_entry = ctk.CTkEntry(
            phase_window,
            placeholder_text="Phase Name"
        )

        phase_entry.pack(
            padx=20,
            pady=20,
            fill="x"
        )

        def save_phase():

            phase_name = phase_entry.get().strip()

            if phase_name == "":
                return

            database.insert_phase(
                phase_name
            )

            phase_window.destroy()

            refresh_phases()

        save_button = ctk.CTkButton(
            phase_window,
            text="Save",
            command=save_phase
        )

        save_button.pack(
            pady=10
        )

    # ساخت اولیه Phaseها
    for index, phase in enumerate(default_phases):

        checkbox = ctk.CTkCheckBox(
            phases_frame,
            text=""
        )

        checkbox.grid(
            row=index + 2,
            column=0,
            padx=15,
            pady=5
        )

        phase_label = ctk.CTkLabel(
            phases_frame,
            text=phase[1],
            font=("Segoe UI", 13)
        )

        phase_label.grid(
            row=index + 2,
            column=1,
            sticky="w",
            padx=10,
            pady=5
        )

        percentage_entry = ctk.CTkEntry(
            phases_frame,
            width=100,
            placeholder_text="%"
        )

        percentage_entry.grid(
            row=index + 2,
            column=2,
            padx=15,
            pady=5
        )

        percentage_entry.configure(
            state="disabled"
        )

        def toggle_phase(
            entry=percentage_entry,
            checkbox=checkbox
        ):

            if checkbox.get() == 1:

                entry.configure(
                    state="normal"
                )

            else:

                entry.delete(
                    0,
                    "end"
                )

                entry.configure(
                    state="disabled"
                )

            update_total()

        checkbox.configure(
            command=toggle_phase
        )

        percentage_entry.bind(
            "<KeyRelease>",
            lambda event: update_total()
        )

        phase_widgets.append(
            (
                checkbox,
                percentage_entry,
                phase[0]
            )
        )

    # =====================================
    # Total
    # =====================================

    total_label = ctk.CTkLabel(
        phases_frame,
        text="Total Weight : 0%",
        font=("Segoe UI", 14)
    )

    total_label.grid(
        row=len(default_phases) + 3,
        column=0,
        columnspan=3,
        sticky="w",
        padx=15,
        pady=(10, 15)
    )

    # =====================================
    # Add Phase Button
    # =====================================

    add_phase_button = ctk.CTkButton(
        phases_frame,
        text="➕ Add Phase",
        width=130,
        command=add_new_phase
    )

    add_phase_button.grid(
        row=len(default_phases) + 4,
        column=0,
        columnspan=3,
        pady=(0, 15)
    )

    # =====================================
    # Description
    # =====================================

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

    description_title = ctk.CTkLabel(
        description_frame,
        text="Description",
        font=FONT_TITLE
    )

    description_title.pack(
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

    # =====================================
    # Save / Cancel
    # =====================================

    buttons_frame = ctk.CTkFrame(
        main_frame,
        fg_color="transparent"
    )

    buttons_frame.pack(
        fill="x",
        pady=(0, 10)
    )

    def save_project():

        code = project_code.get().strip()

        name = project_name.get().strip()

        if code == "":
            code = database.generate_project_code(
                name
            )

        project_type_value = type_combo.get()
        priority_value = priority_combo.get()
        status_value = status_combo.get()

        start = start_date.get().strip()

        end = end_date.get().strip()

        description = description_box.get(
            "1.0",
            "end"
        )

        # =====================================
        # Validation
        # =====================================

        if name == "":
            messagebox.showerror("Add Project", "Project Name is required.")
            return

        # ---- dates -------------------------------------------------

        try:
            project_start_gregorian = jalali_to_gregorian(start)
            project_end_gregorian = jalali_to_gregorian(end)

        except InvalidDateError as error:
            messagebox.showerror("Add Project", str(error))
            return

        if (
            project_start_gregorian
            and project_end_gregorian
            and project_start_gregorian > project_end_gregorian
        ):
            messagebox.showerror(
                "Add Project", "Start Date cannot be after End Date."
            )
            return

        # ---- phases --------------------------------------------------

        total_percentage = 0.0
        selected_phases = []

        for checkbox, entry, phase_id in phase_widgets:

            if checkbox.get() != 1:
                continue

            try:
                percentage = float(entry.get())

            except (ValueError, TypeError):
                messagebox.showerror(
                    "Add Project",
                    "Phase weight must be a valid number."
                )
                return

            if percentage != percentage or percentage in (float("inf"), float("-inf")):
                messagebox.showerror(
                    "Add Project", "Phase weight must be a valid number."
                )
                return

            if not (0 <= percentage <= 100):
                messagebox.showerror(
                    "Add Project", "Phase weight must be between 0 and 100."
                )
                return

            total_percentage += percentage

            selected_phases.append((phase_id, percentage, None, None))

        if len(selected_phases) == 0:
            messagebox.showerror("Add Project", "Select at least one phase.")
            return

        if abs(total_percentage - 100) > 0.01:
            messagebox.showerror(
                "Add Project",
                f"Phase weights must add up to 100%.\n\n"
                f"Current total: {total_percentage:g}%"
            )
            return

        # =====================================
        # Insert Project + Phases  (one transaction)
        # =====================================

        project_data = {
            "project_code": code,
            "project_name": name,
            "client_id": client_map.get(client_combo.get()),
            "department_id": department_map.get(department_combo.get()),
            "manager_id": manager_map.get(manager_combo.get()),
            "project_type": project_type_value,
            "start_date": project_start_gregorian,
            "end_date": project_end_gregorian,
            "priority": priority_value,
            "project_status": status_value,
            "description": description,
        }

        try:
            database.create_project_with_phases(project_data, selected_phases)

        except DuplicateProjectCodeError as error:
            messagebox.showerror("Add Project", str(error))
            return

        except Exception as error:
            messagebox.showerror(
                "Add Project",
                f"Could not save the project:\n\n{error}"
            )
            return

        window.destroy()

    def cancel_project():

        window.destroy()

    save_button = ctk.CTkButton(
        buttons_frame,
        text="💾 Save",
        width=150,
        fg_color=GREEN,
        hover_color=GREEN_HOVER,
        command=save_project
    )

    save_button.pack(
        side="right",
        padx=10
    )

    cancel_button = ctk.CTkButton(
        buttons_frame,
        text="❌ Cancel",
        width=150,
        fg_color=DELETE,
        hover_color=DELETE_HOVER,
        command=cancel_project
    )

    cancel_button.pack(
        side="right"
    )