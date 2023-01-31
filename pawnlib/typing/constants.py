class DateNamespace:
    __slots__ = ()
    MINUTE_IN_SECONDS = 60
    HOUR_IN_SECONDS = 60 * MINUTE_IN_SECONDS
    DAY_IN_SECONDS = 24 * HOUR_IN_SECONDS
    WEEK_IN_SECONDS = 7 * DAY_IN_SECONDS
    MONTH_IN_SECONDS = 30 * DAY_IN_SECONDS
    YEAR_IN_SECONDS = 365 * DAY_IN_SECONDS

    HOUR_IN_MINUTES = 60
    DAY_IN_MINUTES = HOUR_IN_MINUTES * 24


class EtcNamespace(DateNamespace):
    __slots__ = ()
    TRUE = 1
    FALSE = 0
    TINT = 10 ** 18
    ICON_ADDRESS = 42
    ICON_ADDRESS_WITHOUT_PREFIX = 40


class UnixtimeStampDigits(EtcNamespace):
    __slots__ = ()
    SECONDS_DIGITS = 10
    MILLI_SECONDS_DIGITS = 13
    MICRO_SECONDS_DIGITS = 16


const = UnixtimeStampDigits()
