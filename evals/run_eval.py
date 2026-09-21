"""Score persisted extractions against derived golden truth."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select

from evals.golden.generate import GOLDEN_DIR
from evals.scorecard import (
    DocScore,
    ExtractedField,
    dump_scorecard,
    regression_messages,
    render_scorecard,
    score_document,
)
from fundspine.config import REPO_ROOT, settings
from fundspine.ingest.loader import load_html_file
from fundspine.repo.orm import Document, FactRow
from fundspine.repo.session import TenantContext, session_scope

BASELINE_PATH = REPO_ROOT / "evals" / "scorecards" / "baseline.json"


def _load_extracted(stem: str) -> list[ExtractedField]:
    uri = f"golden://{stem}"
    with session_scope(TenantContext.internal()) as session:
        document = session.scalar(select(Document).where(Document.source_uri == uri))
        if document is None:
            raise RuntimeError(f"{stem} has not been ingested; run make ingest")
        rows = list(
            session.scalars(select(FactRow).where(FactRow.document_id == document.document_id))
        )
    if not rows:
        raise RuntimeError(f"{stem} has no facts; ingest produced nothing")
    return [
        ExtractedField(
            field_path=row.field_path,
            period=row.period,
            value_numeric=row.value_numeric,
            value_text=row.value_text,
            page_no=row.page_no,
            quote=row.quote,
        )
        for row in rows
    ]


def run_eval(golden_dir: Path | None = None) -> list[DocScore]:
    dest = golden_dir if golden_dir is not None else GOLDEN_DIR
    scores: list[DocScore] = []
    for stem in ("doc_1", "doc_2", "doc_3"):
        truth = json.loads((dest / f"{stem}.truth.json").read_text(encoding="utf-8"))
        parsed = load_html_file(dest / f"{stem}.html")
        extracted = _load_extracted(stem)
        scores.append(
            score_document(
                stem=stem,
                truth_facts=list(truth["facts"]),
                extracted=extracted,
                pages=parsed.pages,
            )
        )
    return scores


def main() -> int:
    scores = run_eval()
    print(render_scorecard(scores))
    current = dump_scorecard(scores, prompt_version=settings().prompt_version)
    if not BASELINE_PATH.is_file():
        raise RuntimeError(f"missing {BASELINE_PATH}")
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    messages = regression_messages(current, baseline)
    if messages:
        print("REGRESSION vs evals/scorecards/baseline.json")
        for message in messages:
            print(f"  {message}")
        return 1
    print("no regression vs evals/scorecards/baseline.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
