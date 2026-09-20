"""Closed vocabularies. Every cross-layer string in FundSpine is one of these."""

from enum import StrEnum


class DocType(StrEnum):
    TEARSHEET = "tearsheet"
    MONTHLY_LETTER = "monthly_letter"
    PPM = "ppm"


class FactStatus(StrEnum):
    """Facts are append-only; status is the only column that ever changes."""

    CANDIDATE = "candidate"
    VALIDATED = "validated"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class Unit(StrEnum):
    """Integer-only units. There is no float unit and there will not be one.

    BPS carries returns, fees, hurdles and drawdowns (150 = 1.50%).
    RATIO_BPS carries unitless ratios at the same scale (14200 = 1.42x Sharpe).
    USD_CENTS carries money.
    """

    BPS = "bps"
    RATIO_BPS = "ratio_bps"
    USD_CENTS = "usd_cents"
    MONTHS = "months"
    DAYS = "days"
    TEXT = "text"


class FieldPath(StrEnum):
    """The closed set of things this system knows how to extract.

    A closed vocabulary is what makes field-level eval possible: recall is only
    meaningful against a known denominator. An extractor emitting a path not in
    this enum fails validation and the fact is dropped with a recorded reason.
    """

    FUND_NAME = "fund.name"
    FUND_MANAGER_NAME = "fund.manager_name"
    FUND_STRATEGY_FAMILY = "fund.strategy_family"
    FUND_SHARE_CLASS = "fund.share_class"

    METRICS_GROSS_RETURN_BPS = "metrics.gross_return_bps"
    METRICS_NET_RETURN_BPS = "metrics.net_return_bps"
    METRICS_YTD_RETURN_BPS = "metrics.ytd_return_bps"
    METRICS_NAV_USD_CENTS = "metrics.nav_usd_cents"
    METRICS_SHARPE_36M = "metrics.sharpe_36m"
    METRICS_MAX_DRAWDOWN_BPS = "metrics.max_drawdown_bps"

    TERMS_MGMT_FEE_BPS = "terms.mgmt_fee_bps"
    TERMS_PERF_FEE_BPS = "terms.perf_fee_bps"
    TERMS_HURDLE_BPS = "terms.hurdle_bps"
    TERMS_LOCKUP_MONTHS = "terms.lockup_months"
    TERMS_NOTICE_DAYS = "terms.notice_days"

    NARRATIVE_STRATEGY = "narrative.strategy"


class Severity(StrEnum):
    INFO = "info"
    REVIEW = "review"
    BLOCK = "block"


class DriftKind(StrEnum):
    RESTATEMENT = "restatement"
    TERMS_CHANGE = "terms_change"


class DriftStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class RoutingAction(StrEnum):
    ACK = "ack"
    REVIEW = "review"
    BLOCK = "block"


class Tone(StrEnum):
    """Enumerated, not freeform. A freeform per-partner prompt string is
    unversioned, untestable and drifts toward a compliance problem."""

    INSTITUTIONAL_TERSE = "institutional_terse"
    ADVISORY_WARM = "advisory_warm"


class ArtifactKind(StrEnum):
    IC_MEMO = "ic_memo"
    PARTNER_COMMENTARY = "partner_commentary"


class ArtifactStatus(StrEnum):
    RENDERED = "rendered"
    BLOCKED = "blocked"


class GuardCode(StrEnum):
    UNBOUND_NUMERAL = "G1_unbound_numeral"
    BAD_MARKER = "G2_bad_marker"
    CROSS_TENANT = "G3_cross_tenant"
    MISSING_DISCLOSURE = "G4_missing_disclosure"


METRIC_FIELDS: frozenset[FieldPath] = frozenset(
    {
        FieldPath.METRICS_GROSS_RETURN_BPS,
        FieldPath.METRICS_NET_RETURN_BPS,
        FieldPath.METRICS_YTD_RETURN_BPS,
        FieldPath.METRICS_NAV_USD_CENTS,
        FieldPath.METRICS_SHARPE_36M,
        FieldPath.METRICS_MAX_DRAWDOWN_BPS,
    }
)

TERMS_FIELDS: frozenset[FieldPath] = frozenset(
    {
        FieldPath.TERMS_MGMT_FEE_BPS,
        FieldPath.TERMS_PERF_FEE_BPS,
        FieldPath.TERMS_HURDLE_BPS,
        FieldPath.TERMS_LOCKUP_MONTHS,
        FieldPath.TERMS_NOTICE_DAYS,
    }
)

TEXT_FIELDS: frozenset[FieldPath] = frozenset(
    {
        FieldPath.FUND_NAME,
        FieldPath.FUND_MANAGER_NAME,
        FieldPath.FUND_STRATEGY_FAMILY,
        FieldPath.FUND_SHARE_CLASS,
        FieldPath.NARRATIVE_STRATEGY,
    }
)

UNIT_BY_FIELD: dict[FieldPath, Unit] = {
    FieldPath.FUND_NAME: Unit.TEXT,
    FieldPath.FUND_MANAGER_NAME: Unit.TEXT,
    FieldPath.FUND_STRATEGY_FAMILY: Unit.TEXT,
    FieldPath.FUND_SHARE_CLASS: Unit.TEXT,
    FieldPath.NARRATIVE_STRATEGY: Unit.TEXT,
    FieldPath.METRICS_GROSS_RETURN_BPS: Unit.BPS,
    FieldPath.METRICS_NET_RETURN_BPS: Unit.BPS,
    FieldPath.METRICS_YTD_RETURN_BPS: Unit.BPS,
    FieldPath.METRICS_NAV_USD_CENTS: Unit.USD_CENTS,
    FieldPath.METRICS_SHARPE_36M: Unit.RATIO_BPS,
    FieldPath.METRICS_MAX_DRAWDOWN_BPS: Unit.BPS,
    FieldPath.TERMS_MGMT_FEE_BPS: Unit.BPS,
    FieldPath.TERMS_PERF_FEE_BPS: Unit.BPS,
    FieldPath.TERMS_HURDLE_BPS: Unit.BPS,
    FieldPath.TERMS_LOCKUP_MONTHS: Unit.MONTHS,
    FieldPath.TERMS_NOTICE_DAYS: Unit.DAYS,
}
