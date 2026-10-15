import customtkinter as ctk
from tkinter import messagebox

from config import *
from db.lookups import get_values as get_lookup_values

from db.contracts import (
    get_contract_by_id,
    get_contract_projects,
    update_contract
)

from db.clients import get_clients

from utils.jalali_calender import open_jalali_calendar


def edit_contract(tree, on_saved=None):

    # ==========================================
    # Get Selected Contract
    # ==========================================

    selected = tree.selection()

    if not selected:

        messagebox.showwarning(
            "Edit Contract",
            "Please select a contract first."
        )

        return

    values = tree.item(
        selected[0],
        "values"
    )

    contract_id = values[0]

    # ==========================================
    # Get Contract
    # ==========================================

    try:

        contract = get_contract_by_id(
            contract_id
        )

    except Exception as error:

        messagebox.showerror(
            "Database Error",
            str(error)
        )

        return


    if not contract:

        messagebox.showerror(
            "Error",
            "Contract not found."
        )

        return


    (
        contract_id_value,
        project_id,
        client_id,
        contract_name_value,
        contract_number_value,
        contract_value_value,
        paid_amount_value,
        contract_date_value,
        payment_terms_value,
        status_value,
        description_value
    ) = contract


    # ==========================================
    # Window
    # ==========================================

    window = ctk.CTkToplevel()

    window.title(
        "Edit Contract"
    )

    window.geometry(
        "850x720"
    )

    window.minsize(
        750,
        650
    )

    window.grab_set()


    # ==========================================
    # Main Frame
    # ==========================================

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


    title = ctk.CTkLabel(
        main_frame,
        text="Edit Contract",
        font=FONT_TITLE
    )

    title.pack(
        anchor="w",
        pady=(0,15)
    )


    # ==========================================
    # Contract Information
    # ==========================================

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
        0,
        weight=1
    )

    info_frame.grid_columnconfigure(
        1,
        weight=1
    )


    section_title = ctk.CTkLabel(
        info_frame,
        text="Contract Information",
        font=FONT_TITLE
    )

    section_title.grid(
        row=0,
        column=0,
        columnspan=2,
        sticky="w",
        padx=15,
        pady=(15,10)
    )


    # ==========================================
    # Contract Name
    # ==========================================

    contract_name = ctk.CTkEntry(
        info_frame,
        placeholder_text="Contract Name"
    )

    contract_name.insert(
        0,
        contract_name_value or ""
    )

    contract_name.grid(
        row=1,
        column=0,
        sticky="ew",
        padx=(15,7),
        pady=5
    )


    # ==========================================
    # Contract Number
    # ==========================================

    contract_number = ctk.CTkEntry(
        info_frame,
        placeholder_text="Contract Number"
    )

    contract_number.insert(
        0,
        contract_number_value or ""
    )

    contract_number.grid(
        row=1,
        column=1,
        sticky="ew",
        padx=(7,15),
        pady=5
    )


    # ==========================================
    # Projects
    # ==========================================

    projects = get_contract_projects()

    project_values = []
    project_map = {}


    for project in projects:

        p_id = project[0]
        code = project[1] or ""
        name = project[2] or ""

        display = (
            f"{code} - {name}"
        )

        project_values.append(
            display
        )

        project_map[display] = p_id


    project_combo = ctk.CTkComboBox(
        info_frame,
        values=project_values
    )

    project_combo.grid(
        row=2,
        column=0,
        sticky="ew",
        padx=(15,7),
        pady=5
    )


    for name, pid in project_map.items():

        if pid == project_id:

            project_combo.set(
                name
            )

            break


    # ==========================================
    # Clients
    # ==========================================

    clients = get_clients()

    client_values = []
    client_map = {}


    for client in clients:

        cid = client[0]
        cname = client[1]

        client_values.append(
            cname
        )

        client_map[cname] = cid


    client_combo = ctk.CTkComboBox(
        info_frame,
        values=client_values
    )


    client_combo.grid(
        row=2,
        column=1,
        sticky="ew",
        padx=(7,15),
        pady=5
    )


    for name, cid in client_map.items():

        if cid == client_id:

            client_combo.set(
                name
            )

            break


    # ==========================================
    # Contract Value
    # ==========================================

    contract_value = ctk.CTkEntry(
        info_frame,
        placeholder_text="Contract Value"
    )


    contract_value.insert(
        0,
        str(contract_value_value or 0)
    )


    contract_value.grid(
        row=3,
        column=0,
        sticky="ew",
        padx=(15,7),
        pady=5
    )


    # ==========================================
    # Paid Amount
    # ==========================================

    paid_amount = ctk.CTkEntry(
        info_frame,
        placeholder_text="Paid Amount"
    )


    paid_amount.insert(
        0,
        str(paid_amount_value or 0)
    )


    paid_amount.grid(
        row=3,
        column=1,
        sticky="ew",
        padx=(7,15),
        pady=5
    )


    # ==========================================
    # Contract Date
    # ==========================================

    date_frame = ctk.CTkFrame(
        info_frame,
        fg_color="transparent"
    )

    date_frame.grid(
        row=4,
        column=0,
        sticky="ew",
        padx=(15,7),
        pady=5
    )


    date_frame.grid_columnconfigure(
        0,
        weight=1
    )


    date_var = ctk.StringVar()


    contract_date = ctk.CTkEntry(
        date_frame,
        textvariable=date_var,
        placeholder_text="Contract Date"
    )


    contract_date.pack(
        side="left",
        fill="x",
        expand=True
    )


    if contract_date_value:

        date_var.set(
            contract_date_value
        )


    calendar_button = ctk.CTkButton(
        date_frame,
        text="📅",
        width=45
    )


    calendar_button.configure(
        command=lambda: open_jalali_calendar(
            window,
            date_var,
            calendar_button
        )
    )


    calendar_button.pack(
        side="right",
        padx=(5,0)
    )
    # ==========================================
    # Payment Terms
    # ==========================================

    payment_terms = ctk.CTkEntry(
        info_frame,
        placeholder_text="Payment Terms"
    )

    payment_terms.insert(
        0,
        payment_terms_value or ""
    )

    payment_terms.grid(
        row=4,
        column=1,
        sticky="ew",
        padx=(7,15),
        pady=5
    )


    # ==========================================
    # Status
    # ==========================================

    status_combo = ctk.CTkComboBox(
        info_frame,
        values=get_lookup_values("contract_status")
    )

    status_combo.set(
        status_value or "Active"
    )

    status_combo.grid(
        row=5,
        column=0,
        sticky="ew",
        padx=(15,7),
        pady=5
    )


    # ==========================================
    # Description
    # ==========================================

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


    description_title = ctk.CTkLabel(
        description_frame,
        text="Description",
        font=FONT_TITLE
    )

    description_title.pack(
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


    if description_value:

        description_box.insert(
            "1.0",
            description_value
        )


    # ==========================================
    # Save Changes
    # ==========================================

    def save_changes():


        selected_project = project_combo.get()


        new_project_id = project_map.get(
            selected_project
        )


        if new_project_id is None:

            messagebox.showwarning(
                "Validation",
                "Please select a valid project.",
                parent=window
            )

            return



        selected_client = client_combo.get()


        new_client_id = client_map.get(
            selected_client
        )


        if new_client_id is None:

            messagebox.showwarning(
                "Validation",
                "Please select a valid client.",
                parent=window
            )

            return



        new_contract_name = (
            contract_name.get().strip()
        )


        if not new_contract_name:

            messagebox.showwarning(
                "Validation",
                "Contract Name is required.",
                parent=window
            )

            contract_name.focus()

            return



        new_contract_number = (
            contract_number.get().strip()
        )


        if not new_contract_number:

            messagebox.showwarning(
                "Validation",
                "Contract Number is required.",
                parent=window
            )

            contract_number.focus()

            return



        try:

            new_contract_value = float(
                contract_value.get()
            )

            new_paid_amount = float(
                paid_amount.get()
            )


        except ValueError:


            messagebox.showwarning(
                "Validation",
                "Value fields must be numbers.",
                parent=window
            )

            return



        new_contract_date = (
            date_var.get().strip()
        )


        new_payment_terms = (
            payment_terms.get().strip()
        )


        new_status = (
            status_combo.get()
        )


        new_description = description_box.get(
            "1.0",
            "end-1c"
        ).strip()



        # ======================================
        # Database Update
        # ======================================

        try:

            update_contract(
                contract_id=contract_id,
                project_id=new_project_id,
                client_id=new_client_id,
                contract_name=new_contract_name,
                contract_number=new_contract_number,
                contract_value=new_contract_value,
                paid_amount=new_paid_amount,
                contract_date=new_contract_date,
                payment_terms=new_payment_terms,
                status=new_status,
                description=new_description
            )


            messagebox.showinfo(
                "Success",
                "Contract updated successfully.",
                parent=window
            )


            window.destroy()


            if on_saved:

                on_saved()



        except Exception as error:


            messagebox.showerror(
                "Database Error",
                str(error),
                parent=window
            )



    # ==========================================
    # Buttons
    # ==========================================

    buttons_frame = ctk.CTkFrame(
        main_frame,
        fg_color="transparent"
    )

    buttons_frame.pack(
        fill="x",
        pady=(0,10)
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



    update_button = ctk.CTkButton(
        buttons_frame,
        text="💾 Update",
        width=150,
        fg_color=GREEN,
        hover_color=GREEN_HOVER,
        command=save_changes
    )


    update_button.pack(
        side="right",
        padx=10
    )