import datetime
import time
import sys
import math
try:
    from typing import Literal, Optional, Union
except ImportError:
    from typing_extensions import Literal, Optional, Union
from pawnlib.typing.converter import append_zero
from pawnlib.typing.constants import const
from functools import lru_cache

if sys.version_info >= (3, 9):
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    USE_ZONEINFO = True
else:
    USE_ZONEINFO = False
    try:
        import pytz
    except ImportError:
        pytz = None


class TimeCalculator:
    """
    A class to convert seconds into various human-readable string formats.

    :param seconds: The time in seconds to be converted (integer or float).

    Example:

        .. code-block:: python

            tc = TimeCalculator(1224411.5)
            print(tc.to_strings())  # "14 days, 04:06:51"
            print(tc.to_strings(include_ms=True))  # "14 days, 04:06:51.500"
            print(tc.to_minutes())  # 20406
    """

    def __init__(self, seconds: Union[int, float] = 0):
        self._seconds = 0.0
        self._days = 0
        self._hours = 0
        self._minutes = 0
        self._remaining_seconds = 0.0
        self.hhmmss = ""
        self.set_seconds(seconds)

    def set_seconds(self, seconds: Union[int, float]) -> None:
        """
        Set the seconds value and recalculate the time components.

        :param seconds: The time in seconds (integer or float).
        :raises TypeError: If seconds is not an int or float.
        """
        if not isinstance(seconds, (int, float)):
            raise TypeError(f"seconds must be an int or float, got {type(seconds).__name__}")
        self._seconds = float(seconds)  # Convert to float to handle decimals
        self.calculate()

    def calculate(self) -> None:
        """
        Calculate the days, hours, minutes, and remaining seconds from the given seconds.
        """
        seconds = self._seconds
        self._days = math.floor(seconds / const.DAY_IN_SECONDS)
        seconds -= self._days * const.DAY_IN_SECONDS
        self._hours = math.floor(seconds / const.HOUR_IN_SECONDS)
        seconds -= self._hours * const.HOUR_IN_SECONDS
        self._minutes = math.floor(seconds / const.MINUTE_IN_SECONDS)
        self._remaining_seconds = seconds - self._minutes * const.MINUTE_IN_SECONDS
        self.hhmmss = self._format_hhmmss()

    def _format_hhmmss(self, include_ms: bool = False) -> str:
        """
        Format the time components into a string.

        :param include_ms: Whether to include milliseconds in the output.
        :return: The formatted time string.
        """
        if include_ms:
            ms = int((self._remaining_seconds % 1) * 1000)
            sec = int(self._remaining_seconds)
            hhmmss = f"{self._hours:02d}:{self._minutes:02d}:{sec:02d}.{ms:03d}"
        else:
            hhmmss = f"{self._hours:02d}:{self._minutes:02d}:{int(self._remaining_seconds):02d}"
        if self._days:
            day_unit = "day" if self._days == 1 else "days"
            return f"{self._days} {day_unit}, {hhmmss}"
        return hhmmss

    def to_strings(self, format_type: Literal["default", "detailed"] = "default", include_ms: bool = False) -> str:
        """
        Return the calculated time as a string.

        :param format_type: "default" for "days HH:MM:SS", "detailed" for "X days Y hours Z minutes W seconds".
        :param include_ms: Whether to include milliseconds.
        :return: The formatted time string.
        """
        if format_type == "detailed":
            ms_part = f".{int((self._remaining_seconds % 1) * 1000):03d}" if include_ms else ""
            return (f"{self._days} days {self._hours} hours {self._minutes} minutes "
                    f"{int(self._remaining_seconds)}{ms_part} seconds")
        return self._format_hhmmss(include_ms)
    def to_seconds(self) -> int:
        """Convert seconds to total seconds."""
        return int(self._seconds)

    def to_minutes(self) -> int:
        """Convert seconds to total minutes."""
        return int(self._seconds // const.MINUTE_IN_SECONDS)

    def to_hours(self) -> int:
        """Convert seconds to total hours."""
        return int(self._seconds // const.HOUR_IN_SECONDS)

    def to_days(self) -> int:
        """Convert seconds to total days."""
        return int(self._seconds // const.DAY_IN_SECONDS)

    def to_weeks(self) -> int:
        """Convert seconds to total weeks."""
        return int(self._seconds // (const.DAY_IN_SECONDS * 7))

    @classmethod
    def from_hhmmss(cls, hhmmss: str) -> 'TimeCalculator':
        """
        Create a TimeCalculator object from an "HH:MM:SS" string.

        :param hhmmss: Time string in "HH:MM:SS" format.
        :return: A TimeCalculator object.
        """
        h, m, s = map(int, hhmmss.split(':'))
        seconds = h * const.HOUR_IN_SECONDS + m * const.MINUTE_IN_SECONDS + s
        return cls(seconds)

    def __str__(self) -> str:
        return self.to_strings()

    def __repr__(self) -> str:
        return f"TimeCalculator(seconds={self._seconds}, hhmmss='{self.hhmmss}')"   


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


@lru_cache(maxsize=128)
def get_timezone(timezone: str):
    """Cache timezone objects for performance."""
    if USE_ZONEINFO:
        return ZoneInfo(timezone)
    elif pytz:
        try:
            return pytz.timezone(timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            raise ValueError(f"Unknown timezone: {timezone}")
    return None


def todaydate(
    date_type: Optional[Literal[
        "file", "md", "time", "time_sec", "hour", "ms", "log", 
        "log_ms", "ms_text", "unix", "ms_unix"
    ]] = None, 
    target_datetime: datetime.datetime = None,
    timezone: Optional[str] = None
)-> str:
    """
    Returns today's date as a formatted string based on the specified type.

    Args:
        date_type: Optional format type. Options are:
            - None: "YYYYMMDD" (default)
            - "file": "YYYYMMDD_HHMM"
            - "md": "MMDD"
            - "time": "HH:MM:SS.sss"
            - "time_sec": "HH:MM:SS"
            - "hour": "HHMM"
            - "ms" or "log" or "log_ms": "YYYY-MM-DD HH:MM:SS.sss"
            - "ms_text": "YYYYMMDD-HHMMSSsss"
            - "unix": Hexadecimal Unix timestamp (seconds)
            - "ms_unix": Hexadecimal Unix timestamp (microseconds)

        target_datetime: Optional datetime object. Defaults to current time if None.
        timezone: Optional timezone name (e.g., "Asia/Seoul"). Uses system timezone if None or unsupported.

    Returns:
        str: Formatted date string.

    Examples:
        >>> todaydate("ms_unix")
        '0x5e66be4a93496'
        >>> todaydate("log")
        '2025-03-25 12:34:56.789'
    """

    tz = get_timezone(timezone) if timezone else None
    now = target_datetime if target_datetime is not None else datetime.datetime.now(tz)

    formats = {
        None: "%Y%m%d",
        "md": "%m%d",
        "file": "%Y%m%d_%H%M",
        "time": "%H:%M:%S.%f",
        "time_sec": "%H:%M:%S",
        "hour": "%H%M",
        "ms": "%Y-%m-%d %H:%M:%S.%f",
        "log": "%Y-%m-%d %H:%M:%S.%f",
        "log_ms": "%Y-%m-%d %H:%M:%S.%f",
        "ms_text": "%Y%m%d-%H%M%S%f",
    }

    if not isinstance(now, datetime.datetime):
        raise TypeError(f"target_datetime must be a datetime object, got {type(now).__name__}")    

    if date_type in formats:
        result = now.strftime(formats[date_type])
        return result[:-3] if date_type in {"time", "ms", "log", "log_ms", "ms_text"} else result

    if date_type == "unix":
        return hex(int(now.timestamp()))
    if date_type == "ms_unix":
        return hex(int(now.timestamp() * 1_000_000))

    raise ValueError(f"Unsupported date_type: {date_type}")


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


def timestamp_to_string(unix_timestamp: int, str_format: str = '%Y-%m-%d %H:%M:%S', tz: Optional[Union[str, datetime.tzinfo]] = None) -> str:
    """
    Converts a Unix timestamp to a formatted string based on local timezone or specified timezone.

    :param unix_timestamp: Unix timestamp (seconds, milliseconds, or microseconds)
    :param str_format: Output string format (default: '%Y-%m-%d %H:%M:%S')
    :param tz: Timezone as string (e.g., 'UTC', 'Asia/Seoul') or tzinfo object (default: None, uses local timezone)
    :return: Formatted datetime string

    Example:
        .. code-block:: python
            from pawnlib.typing import date_utils

            # Local timezone (default)
            date_utils.timestamp_to_string(12323232323)
            # >> '2360-07-05 09:05:23' (local timezone, e.g., KST)

            # UTC timezone
            date_utils.timestamp_to_string(12323232323, tz='UTC')
            # >> '2360-07-05 00:05:23' (UTC)

            # Asia/Seoul timezone
            date_utils.timestamp_to_string(12323232323, tz='Asia/Seoul')
            # >> '2360-07-05 09:05:23' (Asia/Seoul)
    """
    if isinstance(unix_timestamp, str):
        unix_timestamp = unix_timestamp.strip()
        if not unix_timestamp.isdigit():
            raise ValueError(f"Invalid timestamp format: {unix_timestamp} ({type(unix_timestamp)})")

    ts_length = len(str(unix_timestamp))

    if ts_length == const.SECONDS_DIGITS:
        timestamp_in_seconds = int(unix_timestamp)
    elif ts_length == const.MILLI_SECONDS_DIGITS:
        timestamp_in_seconds = int(unix_timestamp) / 1_000
    elif ts_length == const.MICRO_SECONDS_DIGITS:
        timestamp_in_seconds = int(unix_timestamp) / 1_000_000
    else:
        raise ValueError(f'Invalid timestamp length - length={ts_length}, timestamp={unix_timestamp}')

    
    if isinstance(tz, str):
        try:
            timezone = get_timezone(tz)
        except ZoneInfoNotFoundError as e:
            raise ValueError(f"Unsupported timezone: {tz} ({e})")
    else:
        timezone = tz

    dt = datetime.datetime.fromtimestamp(timestamp_in_seconds, tz=timezone)
    return dt.strftime(str_format)


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
