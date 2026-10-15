import customtkinter as ctk
from tkinter import messagebox
from config import *


def view_contract(tree):

    # ==========================================
    # Selected Contract
    # ==========================================

    selected = tree.selection()

    if not selected:
        messagebox.showwarning(
            "View Contract",
            "Please select a contract first."
        )
        return

    values = tree.item(selected[0], "values")

    contract_id = values[0]
    contract_name = values[1]
    contract_number = values[2]
    project_name = values[3]
    client_name = values[4]
    contract_value = values[5]
    contract_date = values[6]
    status = values[7]

    # ==========================================
    # View Window
    # ==========================================

    window = ctk.CTkToplevel()
    window.title("View Contract")
    window.geometry("600x600")
    window.resizable(False, False)

    window.grab_set()

    # ==========================================
    # Title
    # ==========================================

    title = ctk.CTkLabel(
        window,
        text="Contract Details",
        font=FONT_TITLE,
        text_color=TEXT
    )

    title.pack(
        anchor="w",
        padx=30,
        pady=(25, 20)
    )

    # ==========================================
    # Details Frame
    # ==========================================

    details_frame = ctk.CTkFrame(
        window,
        fg_color=CARD,
        corner_radius=12,
        border_width=1,
        border_color=BORDER
    )

    details_frame.pack(
        fill="both",
        expand=True,
        padx=25,
        pady=(0, 25)
    )

    # ==========================================
    # Details
    # ==========================================

    details = [
        ("Contract ID", contract_id),
        ("Contract Name", contract_name),
        ("Contract Number", contract_number),
        ("Project", project_name),
        ("Client", client_name),
        ("Contract Value", contract_value),
        ("Contract Date", contract_date),
        ("Status", status),
    ]

    for row, (label_text, value) in enumerate(details):

        label = ctk.CTkLabel(
            details_frame,
            text=label_text,
            font=FONT_NORMAL,
            text_color=TEXT2
        )

        label.grid(
            row=row,
            column=0,
            sticky="w",
            padx=25,
            pady=10
        )

        value_label = ctk.CTkLabel(
            details_frame,
            text=value or "-",
            font=FONT_NORMAL,
            text_color=TEXT
        )

        value_label.grid(
            row=row,
            column=1,
            sticky="w",
            padx=25,
            pady=10
        )

    details_frame.grid_columnconfigure(1, weight=1)

    # ==========================================
    # Close Button
    # ==========================================

    close_btn = ctk.CTkButton(
        details_frame,
        text="Close",
        width=120,
        command=window.destroy
    )

    close_btn.grid(
        row=len(details),
        column=0,
        columnspan=2,
        pady=(25, 20)
    )