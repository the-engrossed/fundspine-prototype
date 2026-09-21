from __future__ import annotations

from dataclasses import dataclass

from fundspine.domain.enums import ArtifactKind, FieldPath


@dataclass(frozen=True)
class SectionPlan:
    kind: ArtifactKind
    period: str
    metric_paths: tuple[FieldPath, ...]
    terms_paths: tuple[FieldPath, ...]
    include_drift: bool


_METRICS = (
    FieldPath.METRICS_GROSS_RETURN_BPS,
    FieldPath.METRICS_NET_RETURN_BPS,
    FieldPath.METRICS_YTD_RETURN_BPS,
    FieldPath.METRICS_NAV_USD_CENTS,
    FieldPath.METRICS_SHARPE_36M,
    FieldPath.METRICS_MAX_DRAWDOWN_BPS,
)

_TERMS = (
    FieldPath.TERMS_MGMT_FEE_BPS,
    FieldPath.TERMS_PERF_FEE_BPS,
    FieldPath.TERMS_HURDLE_BPS,
    FieldPath.TERMS_LOCKUP_MONTHS,
    FieldPath.TERMS_NOTICE_DAYS,
)


def plan_partner_commentary(period: str) -> SectionPlan:
    return SectionPlan(
        kind=ArtifactKind.PARTNER_COMMENTARY,
        period=period,
        metric_paths=_METRICS,
        terms_paths=_TERMS,
        include_drift=False,
    )


def plan_ic_memo(period: str) -> SectionPlan:
    return SectionPlan(
        kind=ArtifactKind.IC_MEMO,
        period=period,
        metric_paths=_METRICS,
        terms_paths=_TERMS,
        include_drift=True,
    )
