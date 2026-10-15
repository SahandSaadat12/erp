"""Tiny RBAC helpers shared by every screen (see db/permissions.py)."""

from tkinter import messagebox

from db.permissions import has_permission


def perm_state(current_user, permission):
    """'normal' / 'disabled' for a button's state= argument."""
    return "normal" if has_permission(current_user, permission) else "disabled"


def guarded(current_user, permission, what, action):
    """
    Wrap a button command so it ALSO checks the permission when clicked
    (defence in depth - the button is already disabled in the UI).
    """

    def run(*args, **kwargs):

        if not has_permission(current_user, permission):
            messagebox.showwarning(
                "Permission", f"You don't have permission to {what}."
            )
            return

        return action(*args, **kwargs)

    return run
