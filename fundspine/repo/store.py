"""Fund, document and extraction_run writes. Side effects live here."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from fundspine.domain.ids import (
    DocumentId,
    FundId,
    new_document_id,
    new_extraction_run_id,
)
from fundspine.repo.orm import Document, ExtractionRun, Fund


def get_or_create_fund(
    session: Session,
    *,
    fund_id: FundId,
    name: str,
    manager_name: str,
    strategy_family: str,
    share_class: str,
    currency: str,
    inception_date: date,
    firm_aum_usd_cents: int,
) -> Fund:
    existing = session.get(Fund, fund_id)
    if existing is not None:
        return existing
    row = Fund(
        fund_id=fund_id,
        name=name,
        manager_name=manager_name,
        strategy_family=strategy_family,
        share_class=share_class,
        currency=currency,
        inception_date=inception_date,
        firm_aum_usd_cents=firm_aum_usd_cents,
    )
    session.add(row)
    session.flush()
    return row


def get_document_by_sha256(session: Session, sha256: str) -> Document | None:
    return session.scalar(select(Document).where(Document.sha256 == sha256))


def insert_document(
    session: Session,
    *,
    fund_id: FundId,
    sha256: str,
    doc_type: str,
    period: str,
    source_uri: str,
    page_count: int,
    published_on: date | None,
) -> Document:
    row = Document(
        document_id=new_document_id(),
        fund_id=fund_id,
        sha256=sha256,
        doc_type=doc_type,
        period=period,
        source_uri=source_uri,
        page_count=page_count,
        published_on=published_on,
    )
    session.add(row)
    session.flush()
    return row


def insert_extraction_run(
    session: Session,
    *,
    document_id: DocumentId | UUID,
    model: str,
    prompt_version: str,
    schema_version: str,
    tokens_in: int,
    tokens_out: int,
) -> ExtractionRun:
    row = ExtractionRun(
        extraction_run_id=new_extraction_run_id(),
        document_id=document_id,
        model=model,
        prompt_version=prompt_version,
        schema_version=schema_version,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd_micros=0,
        status="ok",
    )
    session.add(row)
    session.flush()
    return row
