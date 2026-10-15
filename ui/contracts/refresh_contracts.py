from tkinter import messagebox


def refresh_contracts(tree, database):

    try:

        # ===============================
        # Clear Table
        # ===============================

        for item in tree.get_children():
            tree.delete(item)

        # ===============================
        # Get Contracts
        # ===============================

        contracts = database.get_contracts()

        # ===============================
        # Insert Contracts
        # ===============================

        for contract in contracts:

            tree.insert(
                "",
                "end",
                values=(
                    contract[0],
                    contract[1] or "-",
                    contract[2] or "-",
                    contract[3] or "-",
                    contract[4] or "-",
                    contract[5] or "-",
                    contract[6] or "-",
                    contract[7] or "-"
                )
            )

    except Exception as error:

        messagebox.showerror(
            "Refresh Contracts",
            f"Error refreshing contracts:\n\n{error}"
        )