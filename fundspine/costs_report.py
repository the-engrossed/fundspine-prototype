"""Print unit economics from persisted extraction_run token counts."""

from __future__ import annotations

from sqlalchemy import select

from fundspine.costs import cost_micros, mean_micros, render_costs_table
from fundspine.repo.orm import Document, ExtractionRun
from fundspine.repo.session import TenantContext, session_scope


def print_costs() -> None:
    with session_scope(TenantContext.internal()) as session:
        docs = list(session.scalars(select(Document).order_by(Document.source_uri)))
        rows: list[tuple[str, int, int, int]] = []
        for document in docs:
            run = session.scalar(
                select(ExtractionRun).where(
                    ExtractionRun.document_id == document.document_id
                )
            )
            if run is None:
                raise RuntimeError(f"{document.source_uri} has no extraction_run")
            if run.tokens_in == 0 and run.tokens_out == 0:
                raise RuntimeError(
                    f"{document.source_uri} recorded zero tokens; re-run ingest"
                )
            micros = cost_micros(run.tokens_in, run.tokens_out)
            rows.append((document.source_uri, run.tokens_in, run.tokens_out, micros))
    if not rows:
        raise RuntimeError("no extraction runs; run make ingest")
    mean = mean_micros(tuple(row[3] for row in rows))
    print(render_costs_table(rows=rows, mean_document_micros=mean), end="")
