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


class AllConstants(
    TimeConstants,
    BooleanConstants,
    NumericConstants,
    AddressConstants,
    TimeStampDigits,
    ICONConstants,
    HAVAHConstants
):
    __slots__ = ()

    def __setattr__(self, name, value):
        raise TypeError("Constants are read-only")


const = AllConstants()
