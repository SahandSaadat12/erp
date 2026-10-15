from utils.date_converter import gregorian_to_jalali


def refresh_projects(tree, database):

    # =====================================
    # Clear Table
    # =====================================

    for item in tree.get_children():

        tree.delete(item)

    # =====================================
    # Get Projects
    # =====================================

    projects = database.get_projects()

    # =====================================
    # Insert Projects
    # =====================================

    for project in projects:
        tree.insert(
            "",
            "end",
            values=(
                project[0],
                project[1],
                project[2] or "-",
                project[3] or "-",
                f"{float(project[4] or 0):.0f}%",
                project[5],
                gregorian_to_jalali(project[6])
                if project[6]
                else "-",
                gregorian_to_jalali(project[7])
                if project[7]
                else "-"
            )
        )