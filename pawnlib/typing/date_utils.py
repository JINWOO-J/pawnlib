import datetime
import time
try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal
from pawnlib.typing.converter import append_zero
from pawnlib.typing.constants import const


class TimeCalculator:
    """
    A class that converts seconds to a string format.

    :param seconds: The number of seconds to be converted.

    Example:

        .. code-block:: python

            from pawnlib.typing import date_utils
            date_utils.TimeCalculator(1224411)

            # >>  "14 days, 04:06:51"

    """
    def __init__(self, seconds=0):
        self.seconds = seconds
        self._days = 0
        self._hours = 0
        self._minutes = 0
        self._seconds = 0
        self.hhmmss = ""

        self.calculate()

    def calculate(self):
        """
        Calculate the number of days, hours, minutes, and seconds from the given seconds.

        :return: A string representing the number of days, hours, minutes, and seconds.
        """
        seconds = self.seconds
        self._days = int(seconds // const.DAY_IN_SECONDS)
        seconds = int(seconds % const.DAY_IN_SECONDS)
        self._hours = seconds // const.HOUR_IN_SECONDS
        seconds %= const.HOUR_IN_SECONDS
        self._minutes = seconds // const.MINUTE_IN_SECONDS
        seconds %= const.MINUTE_IN_SECONDS
        self._seconds = seconds
        self.hhmmss = "%02i:%02i:%02i" % (self._hours, self._minutes, self._seconds)
        if self._days:
            day_unit = "days"
            if self._days == 1:
                day_unit = "day"
            self.hhmmss = f"{self._days} {day_unit}, {self.hhmmss}"
        return self.hhmmss

    def __str__(self):
        """
        Return the string representation of the calculated time.

        :return: A string representing the number of days, hours, minutes, and seconds.
        """
        return str(self.hhmmss)

    def __repr__(self):
        """
        Return the string representation of the calculated time.

        :return: A string representing the number of days, hours, minutes, and seconds.
        """
        return repr(self.hhmmss)

    def to_strings(self):
        """
        Return the string representation of the calculated time.

        :return: A string representing the number of days, hours, minutes, and seconds.
        """
        return str(self.hhmmss)

    def to_minutes(self):
        """
        Convert the given seconds to minutes.

        :return: The number of minutes.
        """
        return self.seconds // const.MINUTE_IN_SECONDS

    def to_hours(self):
        """
        Convert the given seconds to hours.

        :return: The number of hours.
        """
        return self.seconds // const.HOUR_IN_SECONDS

    def to_days(self):
        """
        Convert the given seconds to days.

        :return: The number of days.
        """
        return self.seconds // const.DAY_IN_SECONDS


def convert_unix_timestamp(date_param):
    """
    Convert a date parameter to a Unix timestamp.

    :param date_param: A date parameter to be converted to a Unix timestamp.
    :type date_param: datetime.datetime or int
    :return: A Unix timestamp.
    :rtype: int

    Example:

        .. code-block:: python

            import datetime

            # Convert a datetime object to a Unix timestamp.
            date = datetime.datetime(2022, 1, 1, 0, 0, 0)
            convert_unix_timestamp(date)
            # >> 1640995200

            # Convert an integer to a Unix timestamp.
            date = 1640995200
            convert_unix_timestamp(date)
            # >> 1640995200
    """
    if isinstance(date_param, datetime.datetime):
        return int(date_param.timestamp())

    if int(date_param) > 1:
        return int(date_param)
    return 0


def get_range_day_of_month(year: int, month: int, return_unix: bool = True):
    """
    This functions will be returned first_day and last_day in parameter.

    :param year:
    :param month:
    :param return_unix:
    :return: (1646060400, 1648738799)

    Example:

        .. code-block:: python

            from pawnlib.typing import date_utils

            date_utils.get_range_day_of_month(year=2022, month=3, return_unix=False)

            # >> ('2022-3-01 00:00:00', '2022-03-31 23:59:59')

    """
    dst_date = datetime.date(year, month, 1)
    next_month = dst_date.replace(day=28) + datetime.timedelta(days=4)
    first_day = f"{year}-{month}-01 00:00:00"
    last_day = f"{next_month - datetime.timedelta(days=next_month.day)} 23:59:59"
    if return_unix:
        first_day = int(time.mktime(datetime.datetime.strptime(first_day, "%Y-%m-%d %H:%M:%S").timetuple()))
        last_day = int(time.mktime(datetime.datetime.strptime(str(last_day), "%Y-%m-%d %H:%M:%S").timetuple()))

    return first_day, last_day


def todaydate(date_type: Literal["file", "time", "time_sec", "hour", "ms", "log", "log_ms", "ms_text", "unix", "ms_unix"] = None) -> str:
    """

    This functions will be returned today date string.

    :param date_type: file, time, time_sec, hour, ms, ms_text, unix, ms_unix
    :return:

    Example:

        .. code-block:: python

            from pawnlib.typing import date_utils

            date_utils.todaydate("ms_unix")
            # >> '0x5e66be4a93496'

            date_utils.todaydate("log")
            # >> '2022-08-17 17:46:47.281'

    """
    if date_type is None:
        return '%s' % datetime.datetime.now().strftime("%Y%m%d")
    elif date_type == "file":
        return '%s' % datetime.datetime.now().strftime("%Y%m%d_%H%M")
    elif date_type == "time":
        return '%s' % datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    elif date_type == "time_sec":
        return '%s' % datetime.datetime.now().strftime("%H:%M:%S")
    elif date_type == "hour":
        return '%s' % datetime.datetime.now().strftime("%H%M")
    elif date_type == "ms" or date_type == "log" or date_type == "log_ms":
        return '%s' % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    elif date_type == "ms_text":
        return '%s' % datetime.datetime.now().strftime("%Y%m%d-%H%M%S%f")[:-3]
    elif date_type == "unix":
        return '%s' % hex(int(datetime.datetime.now().timestamp()))
    elif date_type == "ms_unix":
        return '%s' % hex(int(datetime.datetime.now().timestamp() * 1_000_000))


def format_seconds_to_hhmmss(seconds: int = 0):
    """

    This functions will be returned seconds to hh:mm:ss format

    :param seconds:
    :return:

    Example:

        .. code-block:: python

            from pawnlib.typing import date_utils

            date_utils.format_seconds_to_hhmmss(2323)
            # >> '00:38:43'


    """
    try:
        seconds = int(seconds)
        hours = seconds // const.HOUR_IN_SECONDS
        seconds %= const.HOUR_IN_SECONDS
        minutes = seconds // const.MINUTE_IN_SECONDS
        seconds %= const.MINUTE_IN_SECONDS
        hhmmss = "%02i:%02i:%02i" % (hours, minutes, seconds)
        return hhmmss
    except Exception:
        return seconds


def timestamp_to_string(unix_timestamp: int, str_format='%Y-%m-%d %H:%M:%S'):
    """

    This functions will be returned unix timestamp to hh:mm:ss format

    :param unix_timestamp: unix_timestamp
    :param str_format: string format
    :return:

    Example:

        .. code-block:: python

            from pawnlib.typing import date_utils

            date_utils.timestamp_to_string(12323232323)

            # >> '2360-07-05 09:05:23'


    """
    ts_length = len(str(unix_timestamp))
    if ts_length == const.SECONDS_DIGITS or ts_length == const.MICRO_SECONDS_DIGITS:
        if ts_length == const.MICRO_SECONDS_DIGITS:
            unix_timestamp = unix_timestamp / 1_000_000
        if unix_timestamp:
            return datetime.datetime.fromtimestamp(unix_timestamp).strftime(str_format)
    raise ValueError('Invalid timestamp')


def second_to_dayhhmm(seconds: int = 0):
    """

    This functions will be returned unix timestamp to days hh:mm:ss format

    :param seconds:
    :return:

    Example:

        .. code-block:: python

            from pawnlib.typing import date_utils

            date_utils.second_to_dayhhmm(2132323)

            # >> '24 days 16:18:43'


    """
    day = int(seconds // const.DAY_IN_SECONDS)
    input_time = int(seconds % const.DAY_IN_SECONDS)
    hour = input_time // const.HOUR_IN_SECONDS
    input_time %= const.HOUR_IN_SECONDS
    minutes = input_time // const.MINUTE_IN_SECONDS
    input_time %= const.MINUTE_IN_SECONDS
    sec = input_time

    return f"{day} days {append_zero(hour)}:{append_zero(minutes)}:{append_zero(sec)}"
