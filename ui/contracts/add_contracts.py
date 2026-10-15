import customtkinter as ctk
from tkinter import messagebox

from config import *
from db.lookups import get_values as get_lookup_values

from utils.jalali_calender import open_jalali_calendar
from utils.date_converter import jalali_to_gregorian, InvalidDateError

from db.contracts import (
    get_contract_projects,
    insert_contract
)

from db.clients import get_clients


def add_contract(on_saved=None):

    window = ctk.CTkToplevel()

    window.title(
        "Add Contract"
    )

    window.geometry(
        "800x700"
    )

    window.minsize(
        700,
        600
    )

    window.grab_set()


    # ==================================================
    # Main Frame
    # ==================================================

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


    # ==================================================
    # Title
    # ==================================================

    ctk.CTkLabel(
        main_frame,
        text="Add New Contract",
        font=FONT_TITLE
    ).pack(
        anchor="w",
        pady=(0,15)
    )


    # ==================================================
    # Contract Information
    # ==================================================

    info_frame = ctk.CTkFrame(
        main_frame,
        fg_color=CARD,
        corner_radius=12,
        border_width=1,
        border_color=BORDER
    )

    info_frame.pack(
        fill="x",
        pady=(0,15)
    )


    info_frame.grid_columnconfigure(
        (0,1),
        weight=1
    )


    ctk.CTkLabel(
        info_frame,
        text="Contract Information",
        font=FONT_TITLE
    ).grid(
        row=0,
        column=0,
        columnspan=2,
        sticky="w",
        padx=15,
        pady=15
    )


    # ==================================================
    # Contract Number
    # ==================================================

    contract_number = ctk.CTkEntry(
        info_frame,
        placeholder_text="Contract Number (e.g. CNT-001)"
    )

    contract_number.grid(
        row=1,
        column=0,
        sticky="ew",
        padx=15,
        pady=5
    )


    # ==================================================
    # Contract Name
    # ==================================================

    contract_name = ctk.CTkEntry(
        info_frame,
        placeholder_text="Contract Name"
    )

    contract_name.grid(
        row=2,
        column=0,
        sticky="ew",
        padx=15,
        pady=5
    )


    # ==================================================
    # Projects
    # ==================================================

    try:

        projects = get_contract_projects()

    except Exception as error:

        messagebox.showerror(
            "Database Error",
            str(error),
            parent=window
        )

        window.destroy()

        return


    project_values = []

    project_map = {}


    for project in projects:

        project_id = project[0]

        project_code = project[1] or ""

        project_name = project[2] or ""



        display_name = (
            f"{project_code} - {project_name}"
        )


        project_values.append(
            display_name
        )

        project_map[display_name] = {
            "id": project_id
        }




    # ==================================================
    # Project Combo
    # ==================================================

    project_combo = ctk.CTkComboBox(
        info_frame,
        values=project_values
    )


    project_combo.grid(
        row=1,
        column=1,
        sticky="ew",
        padx=15,
        pady=5
    )


    if project_values:

        project_combo.set(
            project_values[0]
        )

    else:

        project_combo.set(
            "No Projects Found"
        )


    # ==================================================
    # Client
    # ==================================================

    # ==================================================
    # Clients
    # ==================================================

    clients = get_clients()

    client_values = []
    client_map = {}

    for client in clients:
        client_id = client[0]
        client_name = client[1]

        client_values.append(
            client_name
        )

        client_map[client_name] = client_id

    client_combo = ctk.CTkComboBox(
        info_frame,
        values=client_values
    )

    client_combo.grid(
        row=2,
        column=1,
        sticky="ew",
        padx=15,
        pady=5
    )

    if client_values:
        client_combo.set(
            client_values[0]
        )
    else:
        client_combo.set(
            "No Clients Found"
        )




    # ==================================================
    # Contract Value
    # ==================================================

    contract_value = ctk.CTkEntry(
        info_frame,
        placeholder_text="Contract Value"
    )

    contract_value.grid(
        row=4,
        column=0,
        sticky="ew",
        padx=15,
        pady=5
    )


    # ==================================================
    # Paid Amount
    # ==================================================

    paid_amount = ctk.CTkEntry(
        info_frame,
        placeholder_text="Paid Amount (Default: 0)"
    )


    paid_amount.grid(
        row=4,
        column=1,
        sticky="ew",
        padx=15,
        pady=5
    )


    # ==================================================
    # Contract Date (Jalali)
    # ==================================================

    contract_date_var = ctk.StringVar()

    contract_date_entry = ctk.CTkEntry(
        info_frame,
        textvariable=contract_date_var,
        placeholder_text="Select Date"
    )

    contract_date_entry.grid(
        row=5,
        column=0,
        sticky="ew",
        padx=15,
        pady=5
    )


    contract_date_button = ctk.CTkButton(
        info_frame,
        text="📅",
        width=45,
        command=lambda: open_jalali_calendar(
            window,
            contract_date_var,
            contract_date_button
        )
    )


    contract_date_button.grid(
        row=5,
        column=0,
        sticky="e",
        padx=(0,15),
        pady=5
    )


    # ==================================================
    # Payment Terms
    # ==================================================

    payment_terms = ctk.CTkEntry(
        info_frame,
        placeholder_text="Payment Terms (e.g. 30% Advance)"
    )


    payment_terms.grid(
        row=5,
        column=1,
        sticky="ew",
        padx=15,
        pady=5
    )


    # ==================================================
    # Status
    # ==================================================

    status_combo = ctk.CTkComboBox(
        info_frame,
        values=get_lookup_values("contract_status")
    )


    status_combo.set(
        "Active"
    )


    status_combo.grid(
        row=6,
        column=0,
        sticky="ew",
        padx=15,
        pady=5
    )

    # ==================================================
    # Description
    # ==================================================

    description_frame = ctk.CTkFrame(
        main_frame,
        fg_color=CARD,
        corner_radius=12,
        border_width=1,
        border_color=BORDER
    )

    description_frame.pack(
        fill="x",
        pady=(0,15)
    )


    ctk.CTkLabel(
        description_frame,
        text="Description",
        font=FONT_TITLE
    ).pack(
        anchor="w",
        padx=15,
        pady=(15,10)
    )


    description_box = ctk.CTkTextbox(
        description_frame,
        height=130
    )


    description_box.pack(
        fill="x",
        padx=15,
        pady=(0,15)
    )


    # ==================================================
    # Save Contract
    # ==================================================

    def save_contract():


        selected_project = project_combo.get()


        if selected_project not in project_map:

            messagebox.showwarning(
                "Validation",
                "Please select a valid project.",
                parent=window
            )

            return


        project_id = project_map[
            selected_project
        ]["id"]


        contract_number_value = (
            contract_number.get().strip()
        )


        if not contract_number_value:

            messagebox.showwarning(
                "Validation",
                "Contract Number is required.",
                parent=window
            )

            contract_number.focus()

            return


        contract_name_value = (
            contract_name.get().strip()
        )


        if not contract_name_value:

            messagebox.showwarning(
                "Validation",
                "Contract Name is required.",
                parent=window
            )

            contract_name.focus()

            return


        try:

            contract_value_value = float(
                contract_value.get()
            )


        except ValueError:

            messagebox.showwarning(
                "Validation",
                "Contract Value must be a number.",
                parent=window
            )

            contract_value.focus()

            return



        try:

            paid_amount_value = float(
                paid_amount.get()
            )


        except ValueError:

            messagebox.showwarning(
                "Validation",
                "Paid Amount must be a number.",
                parent=window
            )

            paid_amount.focus()

            return



        # ==============================================
        # Convert Jalali Date To Gregorian
        # ==============================================

        contract_date_value = ""


        if contract_date_var.get().strip():

            try:
                contract_date_value = jalali_to_gregorian(
                    contract_date_var.get().strip()
                )

            except InvalidDateError as error:
                messagebox.showerror("Invalid Date", str(error))
                return



        payment_terms_value = (
            payment_terms.get().strip()
        )


        status_value = (
            status_combo.get()
        )


        description_value = description_box.get(
            "1.0",
            "end-1c"
        ).strip()



        # ==============================================
        # Database
        # ==============================================

        try:

            selected_client = client_combo.get()

            client_id = client_map.get(
                selected_client
            )

            insert_contract(

                project_id=project_id,

                client_id=client_id,

                contract_name=contract_name_value,

                contract_number=contract_number_value,

                contract_value=contract_value_value,

                paid_amount=paid_amount_value,

                contract_date=contract_date_value,

                payment_terms=payment_terms_value,

                status=status_value,

                description=description_value

            )


            messagebox.showinfo(
                "Success",
                "Contract added successfully.",
                parent=window
            )


            if on_saved:

                on_saved()


            window.destroy()



        except Exception as error:


            messagebox.showerror(
                "Database Error",
                str(error),
                parent=window
            )



    # ==================================================
    # Buttons
    # ==================================================

    buttons_frame = ctk.CTkFrame(
        main_frame,
        fg_color="transparent"
    )


    buttons_frame.pack(
        fill="x",
        pady=(0,10)
    )



    save_button = ctk.CTkButton(
        buttons_frame,
        text="💾 Save",
        width=150,
        fg_color=GREEN,
        hover_color=GREEN_HOVER,
        command=save_contract
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
        command=window.destroy
    )


    cancel_button.pack(
        side="right"
    )



    # ==================================================
    # Window Close
    # ==================================================

    window.protocol(
        "WM_DELETE_WINDOW",
        window.destroy
    )