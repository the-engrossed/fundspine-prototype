"""Ingest the golden HTML set: parse, extract, validate, persist."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from uuid import UUID

from fundspine.config import REPO_ROOT, settings
from fundspine.domain.enums import FactStatus
from fundspine.domain.ids import DocumentId, ExtractionRunId, FactId, FundId
from fundspine.domain.models import Period
from fundspine.extract.extractor import extract_document
from fundspine.ingest.loader import load_html_file
from fundspine.ingest.materialize import materialize_metrics, materialize_terms, terms_in_force
from fundspine.repo.facts import insert_facts, set_status
from fundspine.repo.session import TenantContext, session_scope
from fundspine.repo.store import (
    get_document_by_sha256,
    get_or_create_fund,
    insert_document,
    insert_extraction_run,
)
from fundspine.validate.rules import R001_fee_bridge, R004_citation_valid
from fundspine.validate.types import ValidationCtx

GOLDEN_DIR = REPO_ROOT / "evals" / "golden"
DOC_STEMS = ("doc_1", "doc_2", "doc_3")


def _load_json(path: Path) -> dict[str, object]:
    payload: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} is not a JSON object")
    return payload


def ingest_golden(golden_dir: Path | None = None) -> None:
    dest = golden_dir if golden_dir is not None else GOLDEN_DIR
    fund_path = dest / "fund.json"
    if not fund_path.is_file():
        raise RuntimeError(f"golden fund.json missing at {fund_path}; run make golden")

    fund_meta = _load_json(fund_path)
    fund_id = FundId(UUID(str(fund_meta["fund_id"])))
    inception = date.fromisoformat(str(fund_meta["inception_date"]))

    with session_scope(TenantContext.internal()) as session:
        get_or_create_fund(
            session,
            fund_id=fund_id,
            name=str(fund_meta["name"]),
            manager_name=str(fund_meta["manager_name"]),
            strategy_family=str(fund_meta["strategy_family"]),
            share_class=str(fund_meta["share_class"]),
            currency=str(fund_meta["currency"]),
            inception_date=inception,
            firm_aum_usd_cents=int(str(fund_meta["firm_aum_usd_cents"])),
        )
        for stem in DOC_STEMS:
            html_path = dest / f"{stem}.html"
            truth_path = dest / f"{stem}.truth.json"
            if not html_path.is_file() or not truth_path.is_file():
                raise RuntimeError(f"missing {stem}; run make golden")
            truth = _load_json(truth_path)
            parsed = load_html_file(html_path)
            existing = get_document_by_sha256(session, parsed.sha256)
            if existing is not None:
                print(f"{stem}: already ingested (sha256={parsed.sha256[:12]}…)")
                continue
            published = date.fromisoformat(str(truth["published_on"]))
            document = insert_document(
                session,
                fund_id=fund_id,
                sha256=parsed.sha256,
                doc_type=str(truth["doc_type"]),
                period=str(truth["period"]),
                source_uri=f"golden://{stem}",
                page_count=parsed.page_count,
                published_on=published,
            )
            period = Period.parse(str(truth["period"]))
            run_row = insert_extraction_run(
                session,
                document_id=document.document_id,
                model=settings().extract_model,
                prompt_version=settings().prompt_version,
                schema_version=settings().schema_version,
                tokens_in=0,
                tokens_out=0,
            )
            extraction = extract_document(
                fund_id=fund_id,
                document_id=DocumentId(document.document_id),
                extraction_run_id=ExtractionRunId(run_row.extraction_run_id),
                pages=parsed.pages,
            )
            run_row.tokens_in = extraction.tokens_in
            run_row.tokens_out = extraction.tokens_out
            insert_facts(session, extraction.facts)
            ctx = ValidationCtx(
                period=period,
                facts=extraction.facts,
                pages=parsed.pages,
                terms=None,
            )
            cite_hits = R004_citation_valid(ctx)
            cite_failed = {v.fact_id for v in cite_hits if v.fact_id is not None}
            for fact in extraction.facts:
                if fact.fact_id in cite_failed:
                    set_status(
                        session,
                        FactId(fact.fact_id),
                        FactStatus.REJECTED,
                        rejected_reason="R004_citation_valid",
                    )
                else:
                    set_status(session, FactId(fact.fact_id), FactStatus.VALIDATED)
            materialize_metrics(
                session,
                fund_id=fund_id,
                period=str(truth["period"]),
                document_id=document.document_id,
            )
            materialize_terms(
                session,
                fund_id=fund_id,
                document_id=document.document_id,
                period=period,
                inception=inception,
            )
            terms = terms_in_force(session, fund_id, period)
            fee_hits = R001_fee_bridge(ValidationCtx(
                period=period,
                facts=extraction.facts,
                pages=parsed.pages,
                terms=terms,
            ))
            violations = (*cite_hits, *fee_hits)
            dropped = len(extraction.dropped)
            print(
                f"{stem}: {len(extraction.facts)} facts kept, {dropped} dropped, "
                f"{len(violations)} rule hits"
            )
            for item in extraction.dropped:
                print(f"  dropped {item.field_path}: {item.reason}")
            for violation in violations:
                print(f"  {violation.rule_id}: {violation.message}")
