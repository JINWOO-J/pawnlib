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
    DEFAULT_ICON_PORT = 9000
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
    def get_name(code: str) -> str:
        """
        Get the human-readable name of an AWS region based on its code.

        :param code: AWS region code (e.g., "us-east-1").
        :return: Human-readable region name (e.g., "US East (N. Virginia)").
        """
        return AWSRegionConstants.REGIONS.get(code, "Unknown region")

    @staticmethod
    def get_list() -> list:
        """
        Get a list of all AWS region codes.

        :return: List of AWS region codes.
        """
        print(AWSRegionConstants.REGIONS.keys())
        return list(AWSRegionConstants.REGIONS.keys())


class AllConstants(
    TimeConstants,
    BooleanConstants,
    NumericConstants,
    AddressConstants,
    TimeStampDigits,
    ICONConstants,
    HAVAHConstants,
    CryptographicConstants,
    NetworkConstants,
    AWSRegionConstants
):
    __slots__ = ()

    def __setattr__(self, name, value):
        raise TypeError("Constants are read-only")

    def get_aws_region_name(self, code: str = "") -> str:
        return self.get_name(code)

    def get_aws_region_list(self) -> list:
        return self.get_list()

const = AllConstants()
