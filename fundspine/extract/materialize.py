"""Turn LLM output into Fact rows. Drops anything that cannot be cited or converted."""

from __future__ import annotations

from dataclasses import dataclass

from fundspine.domain.enums import TEXT_FIELDS, FactStatus, FieldPath, Unit
from fundspine.domain.ids import DocumentId, ExtractionRunId, FundId, new_fact_id
from fundspine.domain.models import Fact, expected_unit
from fundspine.extract.convert import ConversionError, to_integer
from fundspine.extract.schema import LLMExtraction, LLMFact
from fundspine.ingest.loader import Page


@dataclass(frozen=True)
class DroppedFact:
    field_path: str
    reason: str


def _page_text(pages: tuple[Page, ...], page_no: int) -> str | None:
    for page in pages:
        if page.page_no == page_no:
            return page.text
    return None


def _one_fact(
    item: LLMFact,
    *,
    fund_id: FundId,
    document_id: DocumentId,
    extraction_run_id: ExtractionRunId,
    extractor: str,
    pages: tuple[Page, ...],
) -> Fact | DroppedFact:
    try:
        field_path = FieldPath(item.field_path)
    except ValueError:
        return DroppedFact(item.field_path, "unknown field_path")

    text = _page_text(pages, item.page_no)
    if text is None:
        return DroppedFact(item.field_path, f"page {item.page_no} is not in the document")
    if item.quote not in text:
        return DroppedFact(item.field_path, "quote is not a substring of the cited page")

    unit: Unit = expected_unit(field_path)
    value_numeric: int | None = None
    value_text: str | None = None
    if field_path in TEXT_FIELDS:
        value_text = item.value_as_written
    else:
        try:
            value_numeric = to_integer(item.value_as_written, unit)
        except ConversionError as exc:
            return DroppedFact(item.field_path, f"conversion failed: {exc}")

    return Fact(
        fact_id=new_fact_id(),
        fund_id=fund_id,
        document_id=document_id,
        extraction_run_id=extraction_run_id,
        field_path=field_path,
        value_numeric=value_numeric,
        value_text=value_text,
        unit=unit,
        period=item.period,
        page_no=item.page_no,
        quote=item.quote,
        confidence=item.confidence,
        extractor=extractor,
        status=FactStatus.CANDIDATE,
    )


def materialize_facts(
    payload: LLMExtraction,
    *,
    fund_id: FundId,
    document_id: DocumentId,
    extraction_run_id: ExtractionRunId,
    extractor: str,
    pages: tuple[Page, ...],
) -> tuple[tuple[Fact, ...], tuple[DroppedFact, ...]]:
    kept: list[Fact] = []
    dropped: list[DroppedFact] = []
    for item in payload.facts:
        result = _one_fact(
            item,
            fund_id=fund_id,
            document_id=document_id,
            extraction_run_id=extraction_run_id,
            extractor=extractor,
            pages=pages,
        )
        if isinstance(result, DroppedFact):
            dropped.append(result)
        else:
            kept.append(result)
    return tuple(kept), tuple(dropped)
