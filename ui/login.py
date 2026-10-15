"""
Login screen.

Shown before the main window. On success calls on_success({...}) with
the signed-in user's id, name, role AND resolved permission set - every
other screen in the app checks database.has_permission(current_user, ...)
against that set, never a raw role-name string.

Basic brute-force protection: 5 wrong passwords for a username locks
that username for 60 seconds (tracked in session_context - good enough
for a single-desktop ERP; NOT meant to replace a real auth service for
a networked product).
"""

import os
import time
from datetime import datetime, timedelta, timezone

import customtkinter as ctk
from tkinter import messagebox

from config import *
from db.connection import get_connection, set_database_password, PasswordManager
from db.permissions import get_permissions_for_role
from security import verify_password
from paths import DB_PATH
from db import encryption as enc

from db import login_throttle
from db.login_throttle import MAX_ATTEMPTS, LOCKOUT_SECONDS  # noqa: F401


def _user_count():
    connection = get_connection()
    try:
        return connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    except Exception:
        # Do not expose a setup screen if the schema itself is broken.
        return 1
    finally:
        connection.close()


def _get_user(username):

    connection = get_connection()

    try:
        return connection.execute(
            "SELECT id, full_name, password, role, status "
            "FROM users WHERE username = ? COLLATE NOCASE",
            (username,)
        ).fetchone()

    finally:
        connection.close()


def _lock_remaining(username):
    """Seconds this username is still locked (0 = may try)."""
    try:
        return login_throttle.seconds_locked(username)
    except Exception:
        return 0                      # never block sign-in because the counter is unreadable


def _record_failed_attempt(username):
    """Returns (attempts_left, locked_seconds); counters are kept per username."""
    try:
        return login_throttle.record_failure(username)
    except Exception:
        return MAX_ATTEMPTS - 1, 0


def _reset_failed_attempts(username):
    try:
        login_throttle.clear(username)
    except Exception:
        pass


class LoginWindow(ctk.CTkToplevel):

    def __init__(self, app, on_success):

        super().__init__(app)

        self.app = app
        self.on_success = on_success
        self.first_run = _user_count() == 0
        
        # Check if database is encrypted
        self.is_encrypted = os.path.exists(DB_PATH + '.meta')
        
        # Handle encrypted database - show password prompt first
        if self.is_encrypted and not self._prompt_encryption_password():
            self.destroy()
            self.app.destroy()
            return

        self.title("Create Administrator" if self.first_run else "Login")
        self.geometry("420x580" if self.first_run else "420x480")
        self.resizable(False, False)
        self.configure(fg_color=BACKGROUND)
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        ctk.CTkLabel(
            self, text=("Create your first administrator" if self.first_run else APP_TITLE),
            font=("Segoe UI", 22 if self.first_run else 24, "bold"), text_color=TEXT
        ).pack(pady=(34 if self.first_run else 50, 6))

        ctk.CTkLabel(
            self,
            text=("Choose a unique username and a strong password." if self.first_run else "Sign in to continue"),
            font=FONT_NORMAL, text_color=TEXT2
        ).pack(pady=(0, 18 if self.first_run else 30))

        self.full_name = None
        if self.first_run:
            self.full_name = ctk.CTkEntry(
                self, width=280, height=42, placeholder_text="Administrator full name"
            )
            self.full_name.pack(pady=6)

        self.username = ctk.CTkEntry(
            self, width=280, height=42, placeholder_text="Username"
        )
        self.username.pack(pady=8)

        self.password = ctk.CTkEntry(
            self, width=280, height=42, placeholder_text="Password", show="•"
        )
        self.password.pack(pady=8)

        self.error_label = ctk.CTkLabel(
            self, text="", text_color=RED, font=("Segoe UI", 12), wraplength=280
        )
        self.error_label.pack(pady=(4, 10))

        self.submit_button = ctk.CTkButton(
            self, text=("Create Administrator" if self.first_run else "Sign In"), width=280, height=42,
            fg_color=BLUE, hover_color=BLUE_HOVER, command=self._try_login
        )
        self.submit_button.pack(pady=6)

        self.username.bind("<Return>", lambda _e: self.password.focus())
        self.password.bind("<Return>", lambda _e: self._try_login())

        self.transient(app)
        self.after(150, self._take_focus)

    def _prompt_encryption_password(self):
        """Prompt for encryption password if database is encrypted."""
        password_window = ctk.CTkToplevel(self.app)
        password_window.title("Database Encryption Password")
        password_window.geometry("400x300")
        password_window.transient(self.app)
        password_window.grab_set()
        
        ctk.CTkLabel(
            password_window,
            text="Database Encryption Required",
            font=("Segoe UI", 16, "bold"),
            text_color=TEXT
        ).pack(pady=(30, 10))
        
        ctk.CTkLabel(
            password_window,
            text="Enter the master password to decrypt your database.",
            font=FONT_NORMAL,
            text_color=TEXT2
        ).pack(pady=(0, 20))
        
        password_var = ctk.StringVar()
        
        password_entry = ctk.CTkEntry(
            password_window, width=300, height=42, 
            placeholder_text="Enter encryption password", 
            show="•",
            textvariable=password_var
        )
        password_entry.pack(pady=8)
        password_entry.focus()
        
        error_label = ctk.CTkLabel(
            password_window, text="", text_color=RED, font=("Segoe UI", 11), wraplength=300
        )
        error_label.pack(pady=(4, 15))
        
        def on_submit():
            password = password_var.get()
            if not password:
                error_label.configure(text="Please enter the encryption password.")
                return
            
            try:
                # Try to decrypt
                set_database_password(password)
                
                if not enc.ensure_database_decrypted():
                    error_label.configure(text="Incorrect password. Please try again.")
                    return
                
                # Decryption successful
                password_window.destroy()
                
            except Exception as e:
                error_label.configure(text=f"Failed to decrypt: {str(e)[:100]}")
        
        # Enter key support
        password_entry.bind("<Return>", lambda e: on_submit())
        
        submit_button = ctk.CTkButton(
            password_window, text="Decrypt", width=280, height=42,
            fg_color=BLUE, hover_color=BLUE_HOVER, command=on_submit
        )
        submit_button.pack(pady=6)
        
        # Wait for password window to close
        self.app.wait_window(password_window)
        
        # Check if decryption succeeded
        return os.path.exists(DB_PATH) and not os.path.exists(DB_PATH + '.encrypted')

    def _take_focus(self):
        try:
            self.grab_set()
            self.focus_force()
            self.username.focus()
        except Exception:
            pass

    def _is_locked(self, username):
        return _lock_remaining(username)

    def _try_login(self):

        username = self.username.get().strip()
        password = self.password.get()

        if not username or not password:
            self.error_label.configure(text="Enter username and password.")
            return

        if self.first_run:
            full_name = self.full_name.get().strip() if self.full_name else ""
            if not full_name:
                self.error_label.configure(text="Enter the administrator's full name.")
                return
            if len(username) < 3 or any(ch.isspace() for ch in username):
                self.error_label.configure(text="Username must be at least 3 characters and contain no spaces.")
                return
            if len(password) < 12:
                self.error_label.configure(text="Use a password with at least 12 characters.")
                return
            try:
                from db.users import create_first_admin
                create_first_admin(full_name, username, password)
                self.first_run = False
                self.error_label.configure(text="Administrator created. Signing in…")
            except Exception as error:
                self.error_label.configure(text=str(error))
                return

        remaining = self._is_locked(username)

        if remaining:
            self.error_label.configure(
                text=f"Too many attempts. Try again in {remaining}s."
            )
            return

        try:
            row = _get_user(username)

        except Exception as error:
            from utils.app_logger import error as log_error
            log_error("Login database error", exc_info=True)
            self.error_label.configure(text="Unable to sign in. Please try again.")
            return

        if row is None or not verify_password(password, row[2]):

            remaining_attempts, locked_for = _record_failed_attempt(username)

            if locked_for:
                self.error_label.configure(
                    text=f"Too many attempts. Locked for {locked_for}s."
                )
            else:
                self.error_label.configure(
                    text=f"Wrong username or password. "
                         f"({remaining_attempts} attempt(s) left)"
                )

            self.password.delete(0, "end")
            return

        if (row[4] or "Active") != "Active":
            self.error_label.configure(text="This account is disabled.")
            return

        _reset_failed_attempts(username)

        try:                      # move a legacy plain-text password to scrypt
            from db.users import upgrade_legacy_password
            upgrade_legacy_password(row[0], password, row[2])
        except Exception:
            pass                  # never block a valid sign-in because of this

        permissions = get_permissions_for_role(row[3])

        user = {
            "id": row[0],
            "full_name": row[1],
            "role": row[3],
            "permissions": permissions,
        }

        from db.history import set_session_user
        set_session_user(user["id"], username)

        self.destroy()
        self.on_success(user)

    def _cancel(self):
        self.app.destroy()
