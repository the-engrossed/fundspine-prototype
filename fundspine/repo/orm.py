"""SQLAlchemy 2.0 typed ORM. Nine tables, no more.

Storage rules that are not negotiable:
  - every financial value is BigInteger (basis points or cents), never Numeric
  - fact rows are append-only; the only column that changes after insert is
    status, and only on the supersede path in repo/facts.py
  - document.sha256 is UNIQUE, which is what makes re-ingest idempotent
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _pk() -> Mapped[UUID]:
    return mapped_column(PGUUID(as_uuid=True), primary_key=True)


class Fund(Base):
    """Manager name and strategy family live here; there is no manager table."""

    __tablename__ = "fund"

    fund_id: Mapped[UUID] = _pk()
    name: Mapped[str] = mapped_column(String(200))
    manager_name: Mapped[str] = mapped_column(String(200))
    strategy_family: Mapped[str] = mapped_column(String(100))
    share_class: Mapped[str] = mapped_column(String(50))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    inception_date: Mapped[date | None] = mapped_column(Date)
    firm_aum_usd_cents: Mapped[int | None] = mapped_column(BigInteger)


class Document(Base):
    __tablename__ = "document"

    document_id: Mapped[UUID] = _pk()
    fund_id: Mapped[UUID] = mapped_column(ForeignKey("fund.fund_id"))
    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    doc_type: Mapped[str] = mapped_column(String(32))
    period: Mapped[str] = mapped_column(String(8))
    source_uri: Mapped[str] = mapped_column(Text)
    page_count: Mapped[int] = mapped_column(Integer)
    published_on: Mapped[date | None] = mapped_column(Date)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ExtractionRun(Base):
    """One pipeline execution. Joins telemetry to data via trace_id."""

    __tablename__ = "extraction_run"

    extraction_run_id: Mapped[UUID] = _pk()
    document_id: Mapped[UUID] = mapped_column(ForeignKey("document.document_id"))
    model: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[str] = mapped_column(String(16))
    schema_version: Mapped[str] = mapped_column(String(16))
    trace_id: Mapped[str | None] = mapped_column(String(32))
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd_micros: Mapped[int] = mapped_column(BigInteger, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="ok")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FactRow(Base):
    """Append-only. There is no UPDATE path except status -> superseded."""

    __tablename__ = "fact"
    __table_args__ = (
        CheckConstraint(
            "(value_numeric IS NULL) <> (value_text IS NULL)",
            name="ck_fact_exactly_one_value",
        ),
        CheckConstraint(
            "(superseded_by IS NULL) = (status <> 'superseded')",
            name="ck_fact_supersede_pairing",
        ),
        CheckConstraint("page_no >= 1", name="ck_fact_page_no"),
        CheckConstraint("length(quote) >= 3", name="ck_fact_quote_present"),
        Index("ix_fact_lookup", "fund_id", "field_path", "period", "status"),
    )

    fact_id: Mapped[UUID] = _pk()
    fund_id: Mapped[UUID] = mapped_column(ForeignKey("fund.fund_id"))
    document_id: Mapped[UUID] = mapped_column(ForeignKey("document.document_id"))
    extraction_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("extraction_run.extraction_run_id")
    )

    field_path: Mapped[str] = mapped_column(String(64))
    value_numeric: Mapped[int | None] = mapped_column(BigInteger)
    value_text: Mapped[str | None] = mapped_column(Text)
    unit: Mapped[str] = mapped_column(String(16))
    period: Mapped[str | None] = mapped_column(String(8))

    page_no: Mapped[int] = mapped_column(Integer)
    quote: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    extractor: Mapped[str] = mapped_column(String(64))

    status: Mapped[str] = mapped_column(String(16), default="candidate")
    superseded_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    rejected_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FundPeriodMetricsRow(Base):
    """One row per (fund, period). Each value sits beside the fact that produced it."""

    __tablename__ = "fund_period_metrics"
    __table_args__ = (UniqueConstraint("fund_id", "period", name="uq_metrics_fund_period"),)

    fund_id: Mapped[UUID] = mapped_column(ForeignKey("fund.fund_id"), primary_key=True)
    period: Mapped[str] = mapped_column(String(8), primary_key=True)

    gross_return_bps: Mapped[int | None] = mapped_column(BigInteger)
    gross_return_bps_fact_id: Mapped[UUID | None] = mapped_column(ForeignKey("fact.fact_id"))
    net_return_bps: Mapped[int | None] = mapped_column(BigInteger)
    net_return_bps_fact_id: Mapped[UUID | None] = mapped_column(ForeignKey("fact.fact_id"))
    ytd_return_bps: Mapped[int | None] = mapped_column(BigInteger)
    ytd_return_bps_fact_id: Mapped[UUID | None] = mapped_column(ForeignKey("fact.fact_id"))
    nav_usd_cents: Mapped[int | None] = mapped_column(BigInteger)
    nav_usd_cents_fact_id: Mapped[UUID | None] = mapped_column(ForeignKey("fact.fact_id"))
    sharpe_36m: Mapped[int | None] = mapped_column(BigInteger)
    sharpe_36m_fact_id: Mapped[UUID | None] = mapped_column(ForeignKey("fact.fact_id"))
    max_drawdown_bps: Mapped[int | None] = mapped_column(BigInteger)
    max_drawdown_bps_fact_id: Mapped[UUID | None] = mapped_column(ForeignKey("fact.fact_id"))

    materialized_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class TermsRow(Base):
    __tablename__ = "terms"
    __table_args__ = (
        CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from",
            name="ck_terms_range_ordered",
        ),
        Index("ix_terms_fund_effective", "fund_id", "effective_from"),
    )

    terms_id: Mapped[UUID] = _pk()
    fund_id: Mapped[UUID] = mapped_column(ForeignKey("fund.fund_id"))
    mgmt_fee_bps: Mapped[int] = mapped_column(BigInteger)
    perf_fee_bps: Mapped[int] = mapped_column(BigInteger)
    hurdle_bps: Mapped[int] = mapped_column(BigInteger)
    high_water_mark: Mapped[bool] = mapped_column(Boolean, default=True)
    lockup_months: Mapped[int] = mapped_column(Integer)
    notice_days: Mapped[int] = mapped_column(Integer)
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    source_fact_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(PGUUID(as_uuid=True)), default=list
    )


class Partner(Base):
    """The white-label tenant. tone is an enum column, never freeform prompt text."""

    __tablename__ = "partner"

    partner_id: Mapped[UUID] = _pk()
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    brand: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    tone: Mapped[str] = mapped_column(String(32))
    disclosure_block_md: Mapped[str] = mapped_column(Text)
    jurisdiction: Mapped[str] = mapped_column(String(8))
    template_version: Mapped[str] = mapped_column(String(16), default="v1")
    fund_id: Mapped[UUID] = mapped_column(ForeignKey("fund.fund_id"))


class DriftEventRow(Base):
    __tablename__ = "drift_event"
    __table_args__ = (Index("ix_drift_fund_status", "fund_id", "status"),)

    drift_event_id: Mapped[UUID] = _pk()
    fund_id: Mapped[UUID] = mapped_column(ForeignKey("fund.fund_id"))
    kind: Mapped[str] = mapped_column(String(32))
    rule_id: Mapped[str] = mapped_column(String(32))
    severity: Mapped[str] = mapped_column(String(16))
    period: Mapped[str | None] = mapped_column(String(8))
    field_path: Mapped[str | None] = mapped_column(String(64))
    prior_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    prior_fact_id: Mapped[UUID | None] = mapped_column(ForeignKey("fact.fact_id"))
    new_fact_id: Mapped[UUID | None] = mapped_column(ForeignKey("fact.fact_id"))
    hypotheses: Mapped[list[str]] = mapped_column(JSONB, default=list)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="open")
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ArtifactRow(Base):
    """partner_id NULL means internal. blocked_by_drift_id is why a render refused."""

    __tablename__ = "artifact"

    artifact_id: Mapped[UUID] = _pk()
    kind: Mapped[str] = mapped_column(String(32))
    fund_id: Mapped[UUID] = mapped_column(ForeignKey("fund.fund_id"))
    partner_id: Mapped[UUID | None] = mapped_column(ForeignKey("partner.partner_id"))
    period: Mapped[str] = mapped_column(String(8))
    template_version: Mapped[str] = mapped_column(String(16))
    prompt_version: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16))
    render_uri: Mapped[str | None] = mapped_column(Text)
    fact_ids: Mapped[list[UUID]] = mapped_column(ARRAY(PGUUID(as_uuid=True)), default=list)
    guard_violations: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    blocked_by_drift_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("drift_event.drift_event_id")
    )
    blocked_reason: Mapped[str | None] = mapped_column(Text)
    cost_usd_micros: Mapped[int] = mapped_column(BigInteger, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    rendered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
