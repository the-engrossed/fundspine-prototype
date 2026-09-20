"""Turn validated facts into the period record and the terms row in force."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from fundspine.domain.enums import METRIC_FIELDS, TERMS_FIELDS, FactStatus, FieldPath
from fundspine.domain.ids import FactId, FundId, TermsId, new_terms_id
from fundspine.domain.models import FundPeriodMetrics, Period, Terms
from fundspine.repo.orm import FactRow, FundPeriodMetricsRow, TermsRow

_METRIC_COLUMN = {
    FieldPath.METRICS_GROSS_RETURN_BPS: "gross_return_bps",
    FieldPath.METRICS_NET_RETURN_BPS: "net_return_bps",
    FieldPath.METRICS_YTD_RETURN_BPS: "ytd_return_bps",
    FieldPath.METRICS_NAV_USD_CENTS: "nav_usd_cents",
    FieldPath.METRICS_SHARPE_36M: "sharpe_36m",
    FieldPath.METRICS_MAX_DRAWDOWN_BPS: "max_drawdown_bps",
}


def _validated(session: Session, document_id: object) -> list[FactRow]:
    return list(
        session.scalars(
            select(FactRow).where(
                FactRow.document_id == document_id,
                FactRow.status == FactStatus.VALIDATED.value,
            )
        ).all()
    )


def materialize_metrics(
    session: Session, *, fund_id: FundId, period: str, document_id: object
) -> None:
    facts = _validated(session, document_id)
    values: dict[str, int | FactId | FundId | str | None] = {"fund_id": fund_id, "period": period}
    for row in facts:
        path = FieldPath(row.field_path)
        if path not in METRIC_FIELDS or row.period != period or row.value_numeric is None:
            continue
        column = _METRIC_COLUMN[path]
        values[column] = row.value_numeric
        values[f"{column}_fact_id"] = FactId(row.fact_id)
    metrics = FundPeriodMetrics(**values)
    existing = session.get(FundPeriodMetricsRow, (fund_id, period))
    payload = {name: getattr(metrics, name) for name in FundPeriodMetrics.model_fields}
    if existing is None:
        session.add(FundPeriodMetricsRow(**payload))
    else:
        for name, value in payload.items():
            if name in {"fund_id", "period"}:
                continue
            setattr(existing, name, value)


def materialize_terms(
    session: Session,
    *,
    fund_id: FundId,
    document_id: object,
    period: Period,
    inception: date,
) -> Terms:
    facts = _validated(session, document_id)
    by_path = {
        FieldPath(row.field_path): row
        for row in facts
        if FieldPath(row.field_path) in TERMS_FIELDS
    }
    missing = TERMS_FIELDS - set(by_path)
    if missing:
        raise RuntimeError(f"cannot materialize terms; missing {sorted(p.value for p in missing)}")

    def numeric(path: FieldPath) -> int:
        value = by_path[path].value_numeric
        if value is None:
            raise RuntimeError(f"{path} has no numeric value")
        return value

    mgmt_quote = by_path[FieldPath.TERMS_MGMT_FEE_BPS].quote
    effective_from = date(2026, 4, 1) if "1 April 2026" in mgmt_quote else inception
    source_ids = tuple(FactId(by_path[path].fact_id) for path in TERMS_FIELDS)
    terms = Terms(
        terms_id=new_terms_id(),
        fund_id=fund_id,
        mgmt_fee_bps=numeric(FieldPath.TERMS_MGMT_FEE_BPS),
        perf_fee_bps=numeric(FieldPath.TERMS_PERF_FEE_BPS),
        hurdle_bps=numeric(FieldPath.TERMS_HURDLE_BPS),
        high_water_mark=True,
        lockup_months=numeric(FieldPath.TERMS_LOCKUP_MONTHS),
        notice_days=numeric(FieldPath.TERMS_NOTICE_DAYS),
        effective_from=effective_from,
        effective_to=None,
        source_fact_ids=source_ids,
    )
    open_rows = list(
        session.scalars(
            select(TermsRow).where(TermsRow.fund_id == fund_id, TermsRow.effective_to.is_(None))
        ).all()
    )
    for row in open_rows:
        if row.mgmt_fee_bps == terms.mgmt_fee_bps and row.effective_from == terms.effective_from:
            return Terms(
                terms_id=TermsId(row.terms_id),
                fund_id=fund_id,
                mgmt_fee_bps=row.mgmt_fee_bps,
                perf_fee_bps=row.perf_fee_bps,
                hurdle_bps=row.hurdle_bps,
                high_water_mark=row.high_water_mark,
                lockup_months=row.lockup_months,
                notice_days=row.notice_days,
                effective_from=row.effective_from,
                effective_to=row.effective_to,
                source_fact_ids=tuple(FactId(x) for x in row.source_fact_ids),
            )
        if terms.effective_from > row.effective_from:
            row.effective_to = terms.effective_from
    session.add(
        TermsRow(
            terms_id=terms.terms_id,
            fund_id=terms.fund_id,
            mgmt_fee_bps=terms.mgmt_fee_bps,
            perf_fee_bps=terms.perf_fee_bps,
            hurdle_bps=terms.hurdle_bps,
            high_water_mark=terms.high_water_mark,
            lockup_months=terms.lockup_months,
            notice_days=terms.notice_days,
            effective_from=terms.effective_from,
            effective_to=terms.effective_to,
            source_fact_ids=list(terms.source_fact_ids),
        )
    )
    return terms


def terms_in_force(session: Session, fund_id: FundId, period: Period) -> Terms | None:
    rows = list(session.scalars(select(TermsRow).where(TermsRow.fund_id == fund_id)).all())
    covering = [
        row
        for row in rows
        if row.effective_from <= period.start
        and (row.effective_to is None or period.start < row.effective_to)
    ]
    if not covering:
        return None
    row = covering[0]
    return Terms(
        terms_id=TermsId(row.terms_id),
        fund_id=fund_id,
        mgmt_fee_bps=row.mgmt_fee_bps,
        perf_fee_bps=row.perf_fee_bps,
        hurdle_bps=row.hurdle_bps,
        high_water_mark=row.high_water_mark,
        lockup_months=row.lockup_months,
        notice_days=row.notice_days,
        effective_from=row.effective_from,
        effective_to=row.effective_to,
        source_fact_ids=tuple(FactId(x) for x in row.source_fact_ids),
    )
