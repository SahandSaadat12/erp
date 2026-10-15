import customtkinter as ctk
from tkinter import messagebox

from config import *


def view_expense(tree):

    # ==========================================
    # Selected Expense
    # ==========================================

    selected = tree.selection()

    if not selected:

        messagebox.showwarning(
            "View Expense",
            "Please select an expense first."
        )

        return


    values = tree.item(
        selected[0],
        "values"
    )


    expense_id = values[0]
    expense_date = values[1]
    project = values[2]
    title = values[3]
    category = values[4]
    description = values[5]
    amount = values[6]
    paid_by = values[7]
    status = values[8]


    # ==========================================
    # Window
    # ==========================================

    window = ctk.CTkToplevel()

    window.title(
        "View Expense"
    )

    window.geometry(
        "600x650"
    )

    window.resizable(
        False,
        False
    )

    window.grab_set()


    # ==========================================
    # Title
    # ==========================================

    title_label = ctk.CTkLabel(
        window,
        text="Expense Details",
        font=FONT_TITLE,
        text_color=TEXT
    )

    title_label.pack(
        anchor="w",
        padx=30,
        pady=(25,20)
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
        pady=(0,25)
    )


    # ==========================================
    # Details
    # ==========================================

    details = [

        ("Expense ID", expense_id),
        ("Title", title),
        ("Project", project),
        ("Date", expense_date),
        ("Category", category),
        ("Amount", amount),
        ("Paid By", paid_by),
        ("Status", status),
        ("Description", description),

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
            sticky="nw",
            padx=25,
            pady=10
        )


        value_label = ctk.CTkLabel(
            details_frame,
            text=value or "-",
            font=FONT_NORMAL,
            text_color=TEXT,
            wraplength=300,
            justify="left"
        )

        value_label.grid(
            row=row,
            column=1,
            sticky="w",
            padx=25,
            pady=10
        )


    details_frame.grid_columnconfigure(
        1,
        weight=1
    )


    # ==========================================
    # Close
    # ==========================================

    close_button = ctk.CTkButton(
        details_frame,
        text="Close",
        width=120,
        command=window.destroy
    )

    close_button.grid(
        row=len(details),
        column=0,
        columnspan=2,
        pady=(25,20)
    )