from tkinter import messagebox

from db.project_dashboard import project_id_by_code
from .project_dashboard import open_project_dashboard


def view_project(tree, current_user=None, database=None):
    """
    "View" button: opens the Project Controlling dashboard of the
    SELECTED project (looked up by its unique project code).
    """

    selected = tree.selection()

    if not selected:
        messagebox.showwarning("View Project", "Please select a project first.")
        return

    values = tree.item(selected[0], "values")

    if not values:
        return

    if database is not None and not database.has_permission(current_user, "projects.view"):
        messagebox.showwarning("View Project", "You don't have permission to view projects.")
        return

    project_id = project_id_by_code(values[0])

    if project_id is None:
        messagebox.showwarning("View Project", "This project could not be found.")
        return

    open_project_dashboard(
        tree.winfo_toplevel(), project_id,
        current_user=current_user, database=database, tree=tree
    )
