class SpecialCharacterConstants:
    SPECIAL_CHARACTERS = r"_*[]()~`>#+-=|{}.!\\"
    ALL_SPECIAL_CHARACTERS = r"!@#$%^&*()_+-=[]{}|;:'\",.<>?/"


class HTTPConstants:
    class Headers:
        CONTENT_TYPE = "Content-Type"
        AUTHORIZATION = "Authorization"
        USER_AGENT = "User-Agent"
        ACCEPT = "Accept"
        ACCEPT_LANGUAGE = "Accept-Language"
        CACHE_CONTROL = "Cache-Control"
        SET_COOKIE = "Set-Cookie"
        REFERER = "Referer"
        ORIGIN = "Origin"
        HOST = "Host"
        CONNECTION = "Connection"

    class MIMEType:
        APPLICATION_JSON = "application/json"
        APPLICATION_XML = "application/xml"
        APPLICATION_PDF = "application/pdf"
        APPLICATION_OCTET_STREAM = "application/octet-stream"

        TEXT_PLAIN = "text/plain"
        TEXT_HTML = "text/html"
        TEXT_CSS = "text/css"
        TEXT_JAVASCRIPT = "text/javascript"

        IMAGE_JPEG = "image/jpeg"
        IMAGE_PNG = "image/png"
        IMAGE_GIF = "image/gif"
        IMAGE_SVG = "image/svg+xml"

        AUDIO_MP3 = "audio/mpeg"
        AUDIO_WAV = "audio/wav"

        VIDEO_MP4 = "video/mp4"
        VIDEO_WEBM = "video/webm"

        MULTIPART_FORM_DATA = "multipart/form-data"
        APPLICATION_FORM_URLENCODED = "application/x-www-form-urlencoded"

    class HTTPStatusCodes:
        OK = 200
        CREATED = 201
        ACCEPTED = 202
        NO_CONTENT = 204
        BAD_REQUEST = 400
        UNAUTHORIZED = 401
        FORBIDDEN = 403
        NOT_FOUND = 404
        METHOD_NOT_ALLOWED = 405
        CONFLICT = 409
        INTERNAL_SERVER_ERROR = 500
        BAD_GATEWAY = 502
        SERVICE_UNAVAILABLE = 503


class DateFormatConstants:
    ISO_8601 = "%Y-%m-%dT%H:%M:%S"       # Standard ISO 8601 format (e.g., 2023-09-10T14:32:00)
    ISO_8601_WITH_MS = "%Y-%m-%dT%H:%M:%S.%f"  # ISO 8601 with milliseconds (e.g., 2023-09-10T14:32:00.123456)
    ISO_8601_WITH_TZ = "%Y-%m-%dT%H:%M:%S%z"  # ISO 8601 with timezone (e.g., 2023-09-10T14:32:00+0200)

    HUMAN_READABLE = "%A, %d %B %Y %I:%M %p"  # Human-readable format (e.g., Sunday, 10 September 2023 02:32 PM)
    SIMPLE_DATE = "%Y-%m-%d"              # Simple date format (e.g., 2023-09-10)
    SIMPLE_TIME = "%H:%M:%S"              # Simple time format (e.g., 14:32:00)
    SIMPLE_DATETIME = "%Y-%m-%d %H:%M:%S"  # Simple date and time (e.g., 2023-09-10 14:32:00)

    DATE_WITHOUT_YEAR = "%d-%m"           # Date without the year (e.g., 10-09)
    TIME_WITHOUT_SECONDS = "%H:%M"        # Time without seconds (e.g., 14:32)

    US_DATE = "%m/%d/%Y"                  # U.S. style date (e.g., 09/10/2023)
    US_DATE_TIME = "%m/%d/%Y %I:%M %p"    # U.S. style date with 12-hour time (e.g., 09/10/2023 02:32 PM)

    UK_DATE = "%d/%m/%Y"                  # UK style date (e.g., 10/09/2023)
    UK_DATE_TIME = "%d/%m/%Y %H:%M:%S"    # UK style date with time (e.g., 10/09/2023 14:32:00)

    # Unix Timestamp Formats
    UNIX_TIMESTAMP_SECONDS = "%s"         # Unix timestamp (seconds since epoch)
    UNIX_TIMESTAMP_MS = "%f"              # Unix timestamp with milliseconds

    # Custom Formats
    YEAR_ONLY = "%Y"                      # Year only (e.g., 2023)
    MONTH_YEAR = "%B %Y"                  # Month and year (e.g., September 2023)
    DAY_MONTH = "%d %B"                   # Day and month (e.g., 10 September)
    TIME_12_HOUR = "%I:%M %p"             # 12-hour format time (e.g., 02:32 PM)
    TIME_24_HOUR = "%H:%M:%S"             # 24-hour format time (e.g., 14:32:00)


class StringConstants:
    EMPTY_STRING = ""
    SPACE = " "
    UNDERSCORE = "_"
    DASH = "-"
    COLON = ":"
    SEMICOLON = ";"
    COMMA = ","
    PERIOD = "."
    PIPE = "|"
    NEWLINE = "\n"
    TAB = "\t"


class FilePermissionConstants:
    READ_ONLY = "r"
    WRITE_ONLY = "w"
    READ_WRITE = "r+"
    APPEND = "a"
    BINARY_READ = "rb"
    BINARY_WRITE = "wb"
    BINARY_READ_WRITE = "r+b"
    BINARY_APPEND = "ab"


class RegexPatternConstants:
    EMAIL_PATTERN = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    URL_PATTERN = r"^(https?|ftp)://[^\s/$.?#].[^\s]*$"
    PHONE_PATTERN = r"^\+?1?\d{9,15}$"
    POSTAL_CODE_PATTERN = r"^\d{5}(?:[-\s]\d{4})?$"
    IP_ADDRESS_PATTERN = r"^(?:\d{1,3}\.){3}\d{1,3}$"
    CREDIT_CARD_PATTERN = r"^(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})$"
    IPV6_ADDRESS_PATTERN = r"^([0-9a-fA-F]{1,4}:){7}([0-9a-fA-F]{1,4}|:)$"
    HTML_TAG_PATTERN = r"<(\"[^\"]*\"|'[^']*'|[^'\">])*>"
    SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"  # Matches URL slugs (e.g., valid-slug, another-slug)
    INTEGER_PATTERN = r"^-?\d+$" # Matches integers, both positive and negative (e.g., 123, -456)
    FLOAT_PATTERN = r"^-?\d*(\.\d+)?$" # Matches floating point numbers, both positive and negative (e.g., 123.45, -678.90)
    DATE_YYYY_MM_DD_PATTERN = r"^\d{4}-\d{2}-\d{2}$" # Matches date format YYYY-MM-DD (e.g., 2023-09-10)
    TIME_HH_MM_SS_PATTERN = r"^\d{2}:\d{2}:\d{2}$" # Matches time format HH:MM:SS (e.g., 14:32:00)


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
    ICX_IN_LOOP = 10**18
    EXA = 10 ** 18
    PETA = 10 ** 15
    TERA = 10 ** 12
    GIGA = 10 ** 9
    MEGA = 10 ** 6
    KILO = 10 ** 3
    MILLI = 10 ** -3
    MICRO = 10 ** -6
    NANO = 10 ** -9
    SQRT_2 = 2 ** 0.5
    EULER_MASCHERONI = 0.57721  # Euler-Mascheroni
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
    ETH_ADDRESS = 40  # Ethereum address length without '0x' prefix
    ETH_ADDRESS_WITH_PREFIX = 42  # Ethereum address length with '0x' prefix
    BTC_ADDRESS_P2PKH = 34  # Bitcoin P2PKH address length
    BTC_ADDRESS_BECH32 = 42  # Bitcoin Bech32 address length


class TimeStampDigits:
    SECONDS_DIGITS = 10
    MILLI_SECONDS_DIGITS = 13
    MICRO_SECONDS_DIGITS = 16
    NANOSECONDS_DIGITS = 19
    PICOSECONDS_DIGITS = 22
    FEMTOSECONDS_DIGITS = 25


class ICONConstants:
    ICON_METHODS = {
        "cx0000000000000000000000000000000000000001": [
            "getRevision", "getVersion", "getStepPrice", "getStepCosts", "getMaxStepLimit",
            "getScoreStatus", "acceptScore", "rejectScore", "addAuditor", "removeAuditor", "isInScoreBlackList",
            "getProposal", "getProposals", "registerProposal", "voteProposal", "applyProposal",
            "cancelProposal", "onTimer"
        ],
        "cx0000000000000000000000000000000000000000": [
            "disableScore", "enableScore", "acceptScore", "rejectScore", "blockScore", "unblockScore",
            "getBlockedScores", "blockAccount", "unblockAccount", "isBlocked", "setRevision", "setStepPrice",
            "setStepCost", "setMaxStepLimit", "getRevision", "getStepPrice", "getStepCost", "getStepCosts",
            "getMaxStepLimit", "getScoreStatus", "getServiceConfig", "getFeeSharingConfig", "getNetworkInfo",
            "getIISSInfo", "setStake", "getStake", "setDelegation", "getDelegation", "claimIScore",
            "queryIScore", "registerPRep", "getPRep", "unregisterPRep", "setPRep", "getPReps", "getMainPReps",
            "getSubPReps", "setBond", "getBond", "setBonderList", "getBonderList", "estimateUnstakeLockPeriod",
            "getPRepTerm", "getPRepStats", "getPRepStatsOf", "disqualifyPRep", "burn", "validateRewardFund",
            "setRewardFund", "setRewardFundAllocation2", "getScoreOwner", "setScoreOwner", "setNetworkScore",
            "getNetworkScores", "addTimer", "removeTimer", "penalizeNonvoters", "setSlashingRates",
            "getSlashingRates", "setUseSystemDeposit", "getUseSystemDeposit", "getBTPNetworkTypeID",
            "getPRepNodePublicKey", "setPRepNodePublicKey", "registerPRepNodePublicKey", "openBTPNetwork",
            "closeBTPNetwork", "sendBTPMessage", "getMinimumBond", "setMinimumBond", "initCommissionRate",
            "setCommissionRate", "requestUnjail", "handleDoubleSignReport", "setPRepCountConfig",
            "getPRepCountConfig", "setBondRequirementRate"
        ]
    }


class HAVAHConstants:
    HAVAH_METHODS = {
        "cx0000000000000000000000000000000000000001": [
            "setRevision", "setStepPrice", "setStepCost", "setMaxStepLimit", "grantValidator",
            "revokeValidator", "setTimestampThreshold", "setRoundLimitFactor", "setUSDTPrice",
            "setUSDTPriceOracle", "getUSDTPriceOracle", "addPlanetManager", "removePlanetManager",
            "startRewardIssue", "setPrivateClaimableRate", "withdrawLostTo", "registerValidator",
            "enableValidator", "unregisterValidator", "setBlockVoteCheckParameters", "setActiveValidatorCount",
            "name", "openBTPNetwork", "delegate", "setDelegate"
        ],
        "cx0000000000000000000000000000000000000000": [
            "setRevision", "setStepPrice", "setStepCost", "setMaxStepLimit", "getRevision",
            "getStepPrice", "getStepCost", "getStepCosts", "getMaxStepLimit", "getServiceConfig",
            "getScoreOwner", "setScoreOwner", "setRoundLimitFactor", "getRoundLimitFactor", "setUSDTPrice",
            "getUSDTPrice", "getIssueInfo", "startRewardIssue", "addPlanetManager", "removePlanetManager",
            "isPlanetManager", "registerPlanet", "unregisterPlanet", "setPlanetOwner", "getPlanetInfo",
            "reportPlanetWork", "claimPlanetReward", "getRewardInfoOf", "getRewardInfo",
            "setPrivateClaimableRate", "getPrivateClaimableRate", "addDeployer", "removeDeployer", "isDeployer",
            "getDeployers", "setTimestampThreshold", "getTimestampThreshold", "grantValidator",
            "revokeValidator", "getValidators", "getRewardInfosOf", "withdrawLostTo", "getLost",
            "getBTPNetworkTypeID", "getBTPPublicKey", "openBTPNetwork", "closeBTPNetwork", "sendBTPMessage",
            "setBTPPublicKey", "setBlockVoteCheckParameters", "getBlockVoteCheckParameters",
            "registerValidator", "unregisterValidator", "getNetworkStatus", "setValidatorInfo",
            "setNodePublicKey", "enableValidator", "getValidatorInfo", "getValidatorStatus",
            "setActiveValidatorCount", "getActiveValidatorCount", "getValidatorsOf", "getValidatorsInfo",
            "getDisqualifiedValidatorsInfo"
        ]
    }


class CryptographicConstants:
    SHA256_DIGEST_SIZE = 32
    SHA3_256_DIGEST_SIZE = 32
    KECCAK_256_DIGEST_SIZE = 32
    SECP256K1_PRIVATE_KEY_SIZE = 32
    SECP256K1_PUBLIC_KEY_SIZE = 64
    SECP256K1_SIGNATURE_SIZE = 64
    ED25519_PRIVATE_KEY_SIZE = 32
    ED25519_PUBLIC_KEY_SIZE = 32
    ED25519_SIGNATURE_SIZE = 64


class NetworkConstants:
    DEFAULT_HTTP_PORT = 80
    DEFAULT_HTTPS_PORT = 443
    DEFAULT_ICON_RPC_PORT = 9000
    DEFAULT_ICON_P2P_PORT = 7100
    DEFAULT_ETHEREUM_PORT = 8545
    DEFAULT_BITCOIN_PORT = 8333
    LOCALHOST = "127.0.0.1"
    LOCALHOST_IPV6 = "::1"
    IPV4_LOOPBACK = "127.0.0.1"
    IPV6_LOOPBACK = "::1"
    IPV4_BROADCAST = "255.255.255.255"
    IPV6_BROADCAST = "ff02::1"
    MAC_ADDRESS_BROADCAST = "ff:ff:ff:ff:ff:ff"

class AWSRegionConstants:
    REGIONS = {
        "us-east-1": "US East (N. Virginia)",
        "us-east-2": "US East (Ohio)",
        "us-west-1": "US West (N. California)",
        "us-west-2": "US West (Oregon)",
        "ca-central-1": "Canada (Central)",
        "eu-west-1": "EU (Ireland)",
        "eu-west-2": "EU (London)",
        "eu-west-3": "EU (Paris)",
        "eu-central-1": "EU (Frankfurt)",
        "eu-north-1": "EU (Stockholm)",
        "eu-south-1": "EU (Milan)",
        "ap-southeast-1": "Asia Pacific (Singapore)",
        "ap-southeast-2": "Asia Pacific (Sydney)",
        "ap-northeast-1": "Asia Pacific (Tokyo)",
        "ap-northeast-2": "Asia Pacific (Seoul)",
        "ap-northeast-3": "Asia Pacific (Osaka)",
        "ap-east-1": "Asia Pacific (Hong Kong)",
        "ap-south-1": "Asia Pacific (Mumbai)",
        "sa-east-1": "South America (São Paulo)",
        "me-south-1": "Middle East (Bahrain)",
        "af-south-1": "Africa (Cape Town)",
    }

    @staticmethod
    def region_name(code: str) -> str:
        """
        Get the human-readable name of an AWS region based on its code.

        :param code: AWS region code (e.g., "us-east-1").
        :return: Human-readable region name (e.g., "US East (N. Virginia)").
        """
        return AWSRegionConstants.REGIONS.get(code, "Unknown region")

    @staticmethod
    def region_list() -> list:
        """
        Get a list of all AWS region codes.

        :return: List of AWS region codes.
        """
        print(AWSRegionConstants.REGIONS.keys())
        return list(AWSRegionConstants.REGIONS.keys())


class GradeMappingConstants:
    GRADE_MAPPING = {
        "0x0": {"name": "Main", "color": "[blue]\[Main][/blue]"},
        "0x1": {"name": "Sub", "color": "[green]\[Sub][/green]"},
        "0x2": {"name": "Cand", "color": "[Cand]"}
    }

    @staticmethod
    def grade_name(grade_code: str) -> str:
        """
        Get the name associated with the grade code.
        :param grade_code: Grade code (e.g., "0x0").
        :return: Grade name (e.g., "Main").
        """
        return GradeMappingConstants.GRADE_MAPPING.get(grade_code, {}).get("name", "Unknown grade")

    @staticmethod
    def grade_color(grade_code: str) -> str:
        """
        Get the color representation associated with the grade code.
        :param grade_code: Grade code (e.g., "0x0").
        :return: Color representation (e.g., "[blue]\\[Main][/blue]").
        """
        return GradeMappingConstants.GRADE_MAPPING.get(grade_code, {}).get("color", "Unknown color")


class YesNoConstants:
    YES_NO_MAPPING = {
        "0x0": "no",
        "0x1": "yes"
    }

    @staticmethod
    def yes_no(grade_code: str) -> str:
        """
        Get 'yes' or 'no' based on the grade code.
        :param grade_code: Grade code (e.g., "0x0" for 'no', "0x1" for 'yes').
        :return: 'yes' or 'no'.
        """
        return YesNoConstants.YES_NO_MAPPING.get(grade_code, "Unknown code")


class AllConstants(
    SpecialCharacterConstants,
    # HTTPStatusCodes,
    RegexPatternConstants,
    HTTPConstants,
    DateFormatConstants,
    StringConstants,
    FilePermissionConstants,
    TimeConstants,
    # MediaTypeConstants,
    BooleanConstants,
    NumericConstants,
    AddressConstants,
    TimeStampDigits,
    ICONConstants,
    HAVAHConstants,
    CryptographicConstants,
    NetworkConstants,
    AWSRegionConstants,
    GradeMappingConstants,
    YesNoConstants
):
    __slots__ = ()

    def __setattr__(self, name, value):
        raise TypeError("Constants are read-only")

    def get_aws_region_name(self, code: str = "") -> str:
        return self.region_name(code)

    def get_aws_region_list(self) -> list:
        return self.region_list()

const = AllConstants()
