class TimeConstants:
    MINUTE_IN_SECONDS = 60
    HOUR_IN_SECONDS = 60 * MINUTE_IN_SECONDS
    DAY_IN_SECONDS = 24 * HOUR_IN_SECONDS
    WEEK_IN_SECONDS = 7 * DAY_IN_SECONDS
    MONTH_IN_SECONDS = 30 * DAY_IN_SECONDS
    YEAR_IN_SECONDS = 365 * DAY_IN_SECONDS

    MILLISECOND_IN_SECONDS = 0.001
    MICROSECOND_IN_SECONDS = 0.000001
    NANOSECOND_IN_SECONDS = 0.000000001

    HOUR_IN_MINUTES = 60
    DAY_IN_MINUTES = HOUR_IN_MINUTES * 24
    WEEK_IN_MINUTES = 7 * DAY_IN_MINUTES
    MONTH_IN_MINUTES = 30 * DAY_IN_MINUTES
    YEAR_IN_MINUTES = 365 * DAY_IN_MINUTES


class BooleanConstants:
    TRUE = 1
    FALSE = 0


class NumericConstants:
    TINT = 10 ** 18
    PI = 3.14159
    E = 2.71828
    GOLDEN_RATIO = (1 + 5 ** 0.5) / 2


class AddressConstants:
    ICON_ADDRESS = 42
    ICON_ADDRESS_WITHOUT_PREFIX = 40
    # CHAIN_SCORE_ADDRESS = f"cx{'0'*39}0"
    # GOVERNANCE_ADDRESS = f"cx{'0'*39}1"
    CHAIN_SCORE_ADDRESS = "cx0000000000000000000000000000000000000000"
    GOVERNANCE_ADDRESS = "cx0000000000000000000000000000000000000001"


class TimeStampDigits:
    SECONDS_DIGITS = 10
    MILLI_SECONDS_DIGITS = 13
    MICRO_SECONDS_DIGITS = 16
    NANOSECONDS_DIGITS = 19


class AllConstants(
    TimeConstants,
    BooleanConstants,
    NumericConstants,
    AddressConstants,
    TimeStampDigits,
):
    __slots__ = ()

    def __setattr__(self, name, value):
        raise TypeError("Constants are read-only")


const = AllConstants()
