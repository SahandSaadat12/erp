from tkinter import messagebox
from database import archive_cascade


def delete_contract(tree, on_deleted=None):

    # ==========================================
    # Selected Contract
    # ==========================================

    selected = tree.selection()

    if not selected:
        messagebox.showwarning(
            "Delete Contract",
            "Please select a contract first."
        )
        return

    values = tree.item(selected[0], "values")

    contract_id = values[0]
    contract_name = values[1]
    contract_number = values[2]

    # ==========================================
    # Confirmation
    # ==========================================

    answer = messagebox.askyesno(
        "Delete Contract",
        f"Are you sure you want to delete this contract?\n\n"
        f"Name: {contract_name}\n"
        f"Number: {contract_number}\n\n"
        "This contract will be moved to Archive."
    )

    if not answer:
        return

    # ==========================================
    # Archive
    # ==========================================

    try:

        archive_cascade(
            "contracts",
            contract_id
        )

        messagebox.showinfo(
            "Success",
            "Contract moved to Archive successfully."
        )

        # Refresh table
        if on_deleted:
            on_deleted()

    except Exception as error:

        messagebox.showerror(
            "Database Error",
            str(error)
        )