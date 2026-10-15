from tkinter import messagebox

from database import archive_single_record


def delete_selected_expense(
    parent,
    expense_id,
    on_deleted=None
):

    if expense_id is None:

        messagebox.showwarning(
            "Delete Expense",
            "Please select an expense first.",
            parent=parent
        )

        return

    confirm = messagebox.askyesno(
        "Delete Expense",
        "Are you sure you want to delete this expense?\n\n"
        "This expense will be moved to Archive.",
        parent=parent
    )

    if not confirm:
        return

    try:

        archive_single_record(
            "expenses",
            expense_id
        )

    except Exception as error:

        messagebox.showerror(
            "Database Error",
            str(error),
            parent=parent
        )

        return

    messagebox.showinfo(
        "Success",
        "Expense moved to Archive successfully.",
        parent=parent
    )

    if on_deleted:
        on_deleted()