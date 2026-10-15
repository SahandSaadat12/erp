from tkinter import messagebox


def delete_record(
    database,
    tree,
    table_name,
    get_record,
    refresh_function,
    record_name="record",
    cascade=False
):

    selected = tree.selection()

    if not selected:

        messagebox.showwarning(
            "No Selection",
            f"Please select a {record_name} first."
        )

        return


    item = tree.item(
        selected[0]
    )

    values = item.get("values")


    if not values:

        messagebox.showerror(
            "Error",
            "Invalid record data."
        )

        return


    record_identifier = values[0]


    confirm = messagebox.askyesno(
        f"Delete {record_name.title()}",
        f"Are you sure you want to delete "
        f"{record_name}:\n\n{record_identifier}?"
    )


    if not confirm:
        return


    record = get_record(
        record_identifier
    )


    if not record:

        messagebox.showerror(
            "Error",
            f"{record_name.title()} not found."
        )

        return


    record_id = record[0]


    try:

        if cascade:

            database.archive_cascade(
                table_name,
                record_id
            )

        else:

            database.archive_record(
                table_name,
                record_id
            )


        messagebox.showinfo(
            "Success",
            f"{record_name.title()} archived successfully."
        )


        refresh_function(
            tree,
            database
        )


    except Exception as error:

        messagebox.showerror(
            "Delete Error",
            f"Failed to archive {record_name}:\n\n{error}"
        )