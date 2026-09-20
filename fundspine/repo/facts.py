"""Append-only fact persistence. Status is the only column that mutates."""

from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from fundspine.domain.enums import FactStatus
from fundspine.domain.ids import FactId
from fundspine.domain.models import Fact
from fundspine.repo.orm import FactRow


def insert_facts(session: Session, facts: tuple[Fact, ...]) -> None:
    for fact in facts:
        session.add(
            FactRow(
                fact_id=fact.fact_id,
                fund_id=fact.fund_id,
                document_id=fact.document_id,
                extraction_run_id=fact.extraction_run_id,
                field_path=fact.field_path.value,
                value_numeric=fact.value_numeric,
                value_text=fact.value_text,
                unit=fact.unit.value,
                period=fact.period,
                page_no=fact.page_no,
                quote=fact.quote,
                confidence=fact.confidence,
                extractor=fact.extractor,
                status=fact.status.value,
                superseded_by=fact.superseded_by,
            )
        )


def set_status(
    session: Session,
    fact_id: FactId,
    status: FactStatus,
    *,
    rejected_reason: str | None = None,
    superseded_by: FactId | None = None,
) -> None:
    values: dict[str, object] = {"status": status.value, "rejected_reason": rejected_reason}
    if superseded_by is not None:
        values["superseded_by"] = superseded_by
    result = session.execute(
        update(FactRow)
        .where(FactRow.fact_id == fact_id)
        .values(**values)
        .returning(FactRow.fact_id)
    )
    updated = result.scalars().all()
    if len(updated) != 1:
        raise RuntimeError(f"fact {fact_id} was not updated (rowcount={len(updated)})")


def facts_for_document(session: Session, document_id: object) -> list[FactRow]:
    return list(
        session.scalars(select(FactRow).where(FactRow.document_id == document_id)).all()
    )
