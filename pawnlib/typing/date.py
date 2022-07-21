# from datetime import datetime, timedelta, date
import datetime
import time


def convert_unix_timestamp(date_param) -> int:
    """

    :param date_param:
    :return:
    """
    if isinstance(date_param, datetime.datetime):
        return int(date_param.timestamp())

    if int(date_param) > 1:
        return int(date_param)
    return 0


def get_range_day_of_month(year: int, month: int, return_unix: bool = True):
    """
    This functions will be returned first_day and last_day in parameter.

    get_range_day_of_month(year=2022, month=3, return_unix=False)
    => ('2022-3-01 00:00:00', '2022-03-31 23:59:59')
    :param year:
    :param month:
    :param return_unix:
    :return: (1646060400, 1648738799)
    """
    dst_date = datetime.date(year, month, 1)
    next_month = dst_date.replace(day=28) + datetime.timedelta(days=4)
    first_day = f"{year}-{month}-01 00:00:00"
    last_day = f"{next_month - datetime.timedelta(days=next_month.day)} 23:59:59"
    if return_unix:
        first_day = int(time.mktime(datetime.datetime.strptime(first_day, "%Y-%m-%d %H:%M:%S").timetuple()))
        last_day = int(time.mktime(datetime.datetime.strptime(str(last_day), "%Y-%m-%d %H:%M:%S").timetuple()))

    return first_day, last_day


def todaydate(date_type=None):
    """

    :param date_type:
    :return:
    """
    if date_type is None:
        return '%s' % datetime.datetime.now().strftime("%Y%m%d")
    elif date_type == "file":
        return '%s' % datetime.datetime.now().strftime("%Y%m%d_%H%M")
    elif date_type == "time":
        return '%s' % datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    elif date_type == "hour":
        return '%s' % datetime.datetime.now().strftime("%H%M")
    elif date_type == "ms" or date_type == "log" or date_type == "log_ms":
        return '%s' % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    elif date_type == "ms_text":
        return '%s' % datetime.datetime.now().strftime("%Y%m%d-%H%M%S%f")[:-3]


def format_seconds_to_hhmmss(seconds):
    try:
        seconds = int(seconds)
        hours = seconds // (60*60)
        seconds %= (60*60)
        minutes = seconds // 60
        seconds %= 60
        return "%02i:%02i:%02i" % (hours, minutes, seconds)
    except Exception as e:
        return seconds
