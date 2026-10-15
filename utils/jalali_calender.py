import customtkinter as ctk

from persiantools.jdatetime import JalaliDate

from config import (
    CARD,
    HEADER,
    BORDER,
    BLUE,
    BLUE_HOVER,
    GREEN,
    GREEN_HOVER,
    TEXT,
    TEXT2,
    FONT_PERSIAN,
    FONT_PERSIAN_BOLD
)


MONTH_NAMES = [
    "فروردین",
    "اردیبهشت",
    "خرداد",
    "تیر",
    "مرداد",
    "شهریور",
    "مهر",
    "آبان",
    "آذر",
    "دی",
    "بهمن",
    "اسفند"
]


WEEK_DAYS = [
    "شنبه",
    "یکشنبه",
    "دوشنبه",
    "سه‌شنبه",
    "چهارشنبه",
    "پنجشنبه",
    "جمعه"
]


def get_month_days(year, month):

    if month <= 6:
        return 31

    if month <= 11:
        return 30

    if JalaliDate.is_leap(year):
        return 30

    return 29


def open_jalali_calendar(parent, variable, button):

    calendar = ctk.CTkToplevel(parent)

    calendar.title("انتخاب تاریخ")
    calendar.geometry("560x720")
    calendar.minsize(
        560,
        720
    )

    calendar.resizable(
        True,
        True
    )

    calendar.configure(
        fg_color=HEADER
    )

    calendar.transient(parent)
    calendar.grab_set()
    calendar.focus_force()

    # ==========================================================
    # SELECTED DATE
    # ==========================================================

    today = JalaliDate.today()

    selected = {
        "year": today.year,
        "month": today.month,
        "day": today.day
    }

    try:

        value = variable.get().strip()

        if value:

            year, month, day = map(
                int,
                value.replace("-", "/").split("/")
            )

            date = JalaliDate(
                year,
                month,
                day
            )

            selected["year"] = date.year
            selected["month"] = date.month
            selected["day"] = date.day

    except (ValueError, TypeError):
        pass

    # ==========================================================
    # TITLE
    # ==========================================================

    title = ctk.CTkLabel(
        calendar,
        text="انتخاب تاریخ",
        font=FONT_PERSIAN_BOLD,
        text_color=TEXT
    )

    title.pack(
        pady=(20, 15)
    )

    # ==========================================================
    # DATE INPUT
    # ==========================================================

    input_frame = ctk.CTkFrame(
        calendar,
        fg_color=CARD,
        corner_radius=12,
        border_width=1,
        border_color=BORDER
    )

    input_frame.pack(
        fill="x",
        padx=20,
        pady=(0, 15)
    )

    input_frame.grid_columnconfigure(
        (0, 1, 2),
        weight=1
    )

    year_entry = ctk.CTkEntry(
        input_frame,
        placeholder_text="سال",
        justify="center",
        height=42,
        font=FONT_PERSIAN
    )

    year_entry.grid(
        row=0,
        column=0,
        sticky="ew",
        padx=(15, 5),
        pady=15
    )

    month_entry = ctk.CTkEntry(
        input_frame,
        placeholder_text="ماه",
        justify="center",
        height=42,
        font=FONT_PERSIAN
    )

    month_entry.grid(
        row=0,
        column=1,
        sticky="ew",
        padx=5,
        pady=15
    )

    day_entry = ctk.CTkEntry(
        input_frame,
        placeholder_text="روز",
        justify="center",
        height=42,
        font=FONT_PERSIAN
    )

    day_entry.grid(
        row=0,
        column=2,
        sticky="ew",
        padx=(5, 15),
        pady=15
    )

    # ==========================================================
    # ONLY NUMBERS
    # ==========================================================

    def only_numbers(value):

        return value.isdigit() or value == ""

    validation_command = calendar.register(
        only_numbers
    )

    year_entry.configure(
        validate="key",
        validatecommand=(
            validation_command,
            "%P"
        )
    )

    month_entry.configure(
        validate="key",
        validatecommand=(
            validation_command,
            "%P"
        )
    )

    day_entry.configure(
        validate="key",
        validatecommand=(
            validation_command,
            "%P"
        )
    )

    # ==========================================================
    # INITIAL VALUES
    # ==========================================================

    year_entry.insert(
        0,
        str(selected["year"])
    )

    month_entry.insert(
        0,
        f"{selected['month']:02d}"
    )

    day_entry.insert(
        0,
        f"{selected['day']:02d}"
    )

    # ==========================================================
    # MONTH / YEAR CONTROLS
    # ==========================================================

    controls_frame = ctk.CTkFrame(
        calendar,
        fg_color="transparent"
    )

    controls_frame.pack(
        fill="x",
        padx=20,
        pady=(0, 10)
    )

    # ==========================================================
    # YEAR
    # ==========================================================

    year_frame = ctk.CTkFrame(
        controls_frame,
        fg_color=CARD,
        corner_radius=10,
        border_width=1,
        border_color=BORDER
    )

    year_frame.pack(
        side="left",
        fill="x",
        expand=True,
        padx=(0, 5)
    )

    year_minus = ctk.CTkButton(
        year_frame,
        text="−",
        width=40,
        height=35,
        command=lambda: change_year(-1)
    )

    year_minus.pack(
        side="left",
        padx=5,
        pady=7
    )

    year_label = ctk.CTkLabel(
        year_frame,
        text="",
        font=FONT_PERSIAN,
        text_color=TEXT
    )

    year_label.pack(
        side="left",
        expand=True
    )

    year_plus = ctk.CTkButton(
        year_frame,
        text="+",
        width=40,
        height=35,
        command=lambda: change_year(1)
    )

    year_plus.pack(
        side="right",
        padx=5,
        pady=7
    )

    # ==========================================================
    # MONTH
    # ==========================================================

    month_frame = ctk.CTkFrame(
        controls_frame,
        fg_color=CARD,
        corner_radius=10,
        border_width=1,
        border_color=BORDER
    )

    month_frame.pack(
        side="right",
        fill="x",
        expand=True,
        padx=(5, 0)
    )

    month_minus = ctk.CTkButton(
        month_frame,
        text="−",
        width=40,
        height=35,
        command=lambda: change_month(-1)
    )

    month_minus.pack(
        side="left",
        padx=5,
        pady=7
    )

    month_label = ctk.CTkLabel(
        month_frame,
        text="",
        font=FONT_PERSIAN,
        text_color=TEXT
    )

    month_label.pack(
        side="left",
        expand=True
    )

    month_plus = ctk.CTkButton(
        month_frame,
        text="+",
        width=40,
        height=35,
        command=lambda: change_month(1)
    )

    month_plus.pack(
        side="right",
        padx=5,
        pady=7
    )

    # ==========================================================
    # CALENDAR
    # ==========================================================

    calendar_frame = ctk.CTkFrame(
        calendar,
        fg_color=CARD,
        corner_radius=12,
        border_width=1,
        border_color=BORDER
    )

    calendar_frame.pack(
        fill="both",
        expand=True,
        padx=20,
        pady=5
    )

    # ==========================================================
    # UPDATE INPUTS
    # ==========================================================

    def update_inputs():

        year_entry.delete(
            0,
            "end"
        )

        year_entry.insert(
            0,
            str(selected["year"])
        )

        month_entry.delete(
            0,
            "end"
        )

        month_entry.insert(
            0,
            f"{selected['month']:02d}"
        )

        day_entry.delete(
            0,
            "end"
        )

        day_entry.insert(
            0,
            f"{selected['day']:02d}"
        )

    # ==========================================================
    # UPDATE HEADER
    # ==========================================================

    def update_header():

        year_label.configure(
            text=str(
                selected["year"]
            )
        )

        month_label.configure(
            text=MONTH_NAMES[
                selected["month"] - 1
            ]
        )

    # ==========================================================
    # CHANGE YEAR
    # ==========================================================

    def change_year(amount):

        selected["year"] += amount

        max_day = get_month_days(
            selected["year"],
            selected["month"]
        )

        if selected["day"] > max_day:
            selected["day"] = max_day

        update_inputs()
        render_calendar()

    # ==========================================================
    # CHANGE MONTH
    # ==========================================================

    def change_month(amount):

        month = selected["month"] + amount
        year = selected["year"]

        if month < 1:

            month = 12
            year -= 1

        elif month > 12:

            month = 1
            year += 1

        selected["month"] = month
        selected["year"] = year

        max_day = get_month_days(
            year,
            month
        )

        if selected["day"] > max_day:
            selected["day"] = max_day

        update_inputs()
        render_calendar()

    # ==========================================================
    # CHANGE DAY
    # ==========================================================

    def change_day(amount):

        new_day = selected["day"] + amount

        max_day = get_month_days(
            selected["year"],
            selected["month"]
        )

        if new_day < 1:

            change_month(-1)

            selected["day"] = get_month_days(
                selected["year"],
                selected["month"]
            )

        elif new_day > max_day:

            change_month(1)

            selected["day"] = 1

        else:

            selected["day"] = new_day

        update_inputs()
        render_calendar()

    # ==========================================================
    # READ MANUAL DATE
    # ==========================================================

    def read_manual_date():

        try:

            year = int(
                year_entry.get()
            )

            month = int(
                month_entry.get()
            )

            day = int(
                day_entry.get()
            )

            if month < 1 or month > 12:
                return False

            max_day = get_month_days(
                year,
                month
            )

            if day < 1 or day > max_day:
                return False

            JalaliDate(
                year,
                month,
                day
            )

            selected["year"] = year
            selected["month"] = month
            selected["day"] = day

            return True

        except (ValueError, TypeError):

            return False

    # ==========================================================
    # SELECT DATE
    # ==========================================================

    def select_date(day):

        selected["day"] = day

        save_date()

    # ==========================================================
    # SAVE DATE
    # ==========================================================

    def save_date():

        if not read_manual_date():

            return

        date_text = (
            f"{selected['year']:04d}-"
            f"{selected['month']:02d}-"
            f"{selected['day']:02d}"
        )

        variable.set(
            date_text
        )

        button.configure(
            text=f"📅 {date_text}"
        )

        calendar.destroy()

    # ==========================================================
    # TODAY
    # ==========================================================

    def set_today():

        today_date = JalaliDate.today()

        selected["year"] = today_date.year
        selected["month"] = today_date.month
        selected["day"] = today_date.day

        update_inputs()
        render_calendar()

    # ==========================================================
    # RENDER CALENDAR
    # ==========================================================

    def render_calendar():

        for widget in calendar_frame.winfo_children():
            widget.destroy()

        update_header()

        # ------------------------------------------------------
        # WEEK DAYS
        # ------------------------------------------------------

        for column in range(7):

            calendar_frame.grid_columnconfigure(
                column,
                weight=1
            )

            label = ctk.CTkLabel(
                calendar_frame,
                text=WEEK_DAYS[column],
                font=FONT_PERSIAN,
                text_color=TEXT2
            )

            label.grid(
                row=0,
                column=column,
                padx=2,
                pady=(12, 8)
            )

        # ------------------------------------------------------
        # FIRST DAY
        # ------------------------------------------------------

        first_day = JalaliDate(
            selected["year"],
            selected["month"],
            1
        ).to_gregorian()

        first_column = (
            first_day.weekday() + 2
        ) % 7

        days_in_month = get_month_days(
            selected["year"],
            selected["month"]
        )

        row = 1
        column = first_column

        # ------------------------------------------------------
        # DAYS
        # ------------------------------------------------------

        for day in range(
            1,
            days_in_month + 1
        ):

            selected_day = (
                day == selected["day"]
            )

            day_button = ctk.CTkButton(
                calendar_frame,
                text=str(day),
                width=48,
                height=38,
                font=FONT_PERSIAN,
                fg_color=(
                    BLUE
                    if selected_day
                    else "transparent"
                ),
                hover_color=BLUE_HOVER,
                text_color=TEXT,
                command=lambda d=day: select_date(d)
            )

            day_button.grid(
                row=row,
                column=column,
                padx=3,
                pady=3
            )

            column += 1

            if column > 6:

                column = 0
                row += 1

    # ==========================================================
    # DAY BUTTONS
    # ==========================================================

    day_controls = ctk.CTkFrame(
        calendar,
        fg_color="transparent"
    )

    day_controls.pack(
        fill="x",
        padx=20,
        pady=10
    )

    previous_day = ctk.CTkButton(
        day_controls,
        text="‹",
        width=55,
        height=36,
        font=FONT_PERSIAN_BOLD,
        command=lambda: change_day(-1)
    )

    previous_day.pack(
        side="left"
    )

    today_button = ctk.CTkButton(
        day_controls,
        text="امروز",
        width=110,
        height=36,
        font=FONT_PERSIAN,
        fg_color=GREEN,
        hover_color=GREEN_HOVER,
        command=set_today
    )

    today_button.pack(
        side="left",
        expand=True
    )

    next_day = ctk.CTkButton(
        day_controls,
        text="›",
        width=55,
        height=36,
        font=FONT_PERSIAN_BOLD,
        command=lambda: change_day(1)
    )

    next_day.pack(
        side="right"
    )

    # ==========================================================
    # SAVE
    # ==========================================================

    save_button = ctk.CTkButton(
        calendar,
        text="ذخیره تاریخ",
        height=38,
        font=FONT_PERSIAN_BOLD,
        fg_color=BLUE,
        hover_color=BLUE_HOVER,
        command=save_date
    )

    save_button.pack(
        fill="x",
        padx=20,
        pady=(0, 20)
    )

    # ==========================================================
    # INITIAL RENDER
    # ==========================================================

    render_calendar()