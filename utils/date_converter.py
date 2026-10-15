from datetime import datetime

from persiantools.jdatetime import JalaliDate


class InvalidDateError(ValueError):
    """Raised when a date string is not a valid Jalali/Gregorian date."""
    pass


def jalali_to_gregorian(date):
    """
    Converts a Jalali (Shamsi) date string ("1404/05/12") to the
    Gregorian "YYYY-MM-DD" format stored in the database.

    Returns None for an empty/None input (that's a valid "no date").
    Raises InvalidDateError for anything that isn't a real calendar date -
    it NEVER returns the broken input, so a bad date can't silently end
    up stored in the database.
    """

    if date is None:
        return None

    text = str(date).strip()

    if text == "":
        return None

    text = text.replace("-", "/")

    parts = text.split("/")

    if len(parts) != 3:
        raise InvalidDateError(
            f"'{date}' is not a valid date (expected YYYY/MM/DD)."
        )

    try:
        year, month, day = (int(p) for p in parts)
        jalali = JalaliDate(year, month, day)
        gregorian = jalali.to_gregorian()

    except (ValueError, TypeError) as error:
        raise InvalidDateError(f"'{date}' is not a valid date.") from error

    return f"{gregorian.year:04d}-{gregorian.month:02d}-{gregorian.day:02d}"


def gregorian_to_jalali(date):
    """
    Converts a "YYYY-MM-DD" Gregorian date (as stored in the database)
    to a Jalali "YYYY/MM/DD" string for display.

    Returns "" for an empty/None input, and "" for a value that cannot
    be parsed (display-only - never raises, so a table row with a bad
    stored date still renders instead of crashing the whole screen).
    """

    if not date:
        return ""

    text = str(date).strip()

    if "/" in text:
        # already Jalali (some older rows may have been stored this way)
        return text

    try:
        text = text.split(" ")[0]
        gregorian = datetime.strptime(text, "%Y-%m-%d")
        jalali = JalaliDate(gregorian)

        return f"{jalali.year:04d}/{jalali.month:02d}/{jalali.day:02d}"

    except (ValueError, TypeError):
        return ""
