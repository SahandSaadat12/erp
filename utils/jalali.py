from datetime import datetime
from persiantools.jdatetime import JalaliDate


DATE_FORMAT = "%Y-%m-%d"


def gregorian_to_jalali(value):

    if not value:
        return ""

    try:
        date = datetime.strptime(
            str(value),
            DATE_FORMAT
        ).date()

        jalali = JalaliDate(date)

        return jalali.strftime("%Y/%m/%d")

    except (ValueError, TypeError):

        return str(value)


def jalali_to_gregorian(value):

    if not value:
        return ""

    try:
        jalali = JalaliDate.strptime(
            str(value),
            "%Y/%m/%d"
        )

        gregorian = jalali.to_gregorian()

        return gregorian.strftime(
            DATE_FORMAT
        )

    except (ValueError, TypeError):

        return str(value)


def today_jalali():

    return JalaliDate.today().strftime(
        "%Y/%m/%d"
    )


def today_gregorian():

    return datetime.now().strftime(
        DATE_FORMAT
    )