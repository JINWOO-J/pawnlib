# from datetime import datetime, timedelta, date
import datetime
import time
from pawnlib.typing.converter import append_zero


class TimeCalculator:
    def __init__(self, seconds=0):
        """
        It will be calculated seconds to string format

        :param seconds:

        Example:

            .. code-block:: python

                from pawnlib.typing import date_utils
                date_utils.time_calculator = TimeCalculator(1224411)

                # >>  "14 days, 04:06:51"

        """
        self.seconds = seconds
        self._days = 0
        self._hours = 0
        self._minutes = 0
        self._seconds = 0
        self.hhmmss = ""

        self.calculate()

    def calculate(self):
        seconds = self.seconds
        self._days = int(seconds // (24 * 3600))
        seconds = int(seconds % (24 * 3600))
        self._hours = seconds // 3600
        seconds %= 3600
        self._minutes = seconds // 60
        seconds %= 60
        self._seconds = seconds
        self.hhmmss = "%02i:%02i:%02i" % (self._hours, self._minutes, self._seconds)
        if self._days:
            day_unit = "days"
            if self._days == 1:
                day_unit = "day"
            self.hhmmss = f"{self._days} {day_unit}, {self.hhmmss}"
        return self.hhmmss

    def __str__(self):
        return str(self.hhmmss)

    def __repr__(self):
        # https://stackoverflow.com/questions/33229036/why-doesnt-this-repr-function-return-a-string
        # __repr__ returns not string
        # It doesn't work well.
        # An error occurs in the asertEqual() of unittest.
        # return self.hhmmss
        return repr(self.hhmmss)

    def to_strings(self):
        return str(self.hhmmss)

    def to_minutes(self):
        return self.seconds // 60

    def to_hours(self):
        return self.seconds // 3600

    def to_days(self):
        return self.seconds // (24 * 3600)


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
        hhmmss = "%02i:%02i:%02i" % (hours, minutes, seconds)
        return hhmmss
    except Exception as e:
        return seconds


def timestamp_to_string(unix_timestamp, str_format='%Y-%m-%d %H:%M:%S'):

    ts_length = len(str(unix_timestamp))
    # seconds
    if ts_length == 10:
        pass
    # milli seconds
    elif ts_length == 16:
        unix_timestamp = unix_timestamp/1_000_000
    if unix_timestamp:
        return datetime.datetime.fromtimestamp(unix_timestamp).strftime(str_format)


def second_to_dayhhmm(input_time):
    day = int(input_time // (24 * 3600))
    input_time = int(input_time % (24 * 3600))
    hour = input_time // 3600
    input_time %= 3600
    minutes = input_time // 60
    input_time %= 60
    seconds = input_time

    return f"{day} days {append_zero(hour)}:{append_zero(minutes)}:{append_zero(seconds)}"
