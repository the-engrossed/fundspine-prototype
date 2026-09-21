"""Load golden truth as validated facts so render can run without a live extract."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from evals.golden.generate import GOLDEN_DIR
from fundspine.domain.enums import FactStatus, FieldPath, Unit
from fundspine.domain.ids import DocumentId, ExtractionRunId, FactId, FundId
from fundspine.domain.models import Fact


def _stable_id(name: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"fundspine:{name}")


def facts_from_golden(stem: str, golden_dir: Path | None = None) -> tuple[Fact, ...]:
    dest = golden_dir if golden_dir is not None else GOLDEN_DIR
    fund = json.loads((dest / "fund.json").read_text(encoding="utf-8"))
    truth = json.loads((dest / f"{stem}.truth.json").read_text(encoding="utf-8"))
    fund_id = FundId(UUID(str(fund["fund_id"])))
    document_id = DocumentId(_stable_id(f"document:{stem}"))
    run_id = ExtractionRunId(_stable_id(f"run:{stem}"))
    facts: list[Fact] = []
    for index, row in enumerate(truth["facts"]):
        path = FieldPath(str(row["field_path"]))
        unit = Unit(str(row["unit"]))
        payload: dict[str, object] = {
            "fact_id": FactId(_stable_id(f"fact:{stem}:{index}:{path.value}")),
            "fund_id": fund_id,
            "document_id": document_id,
            "extraction_run_id": run_id,
            "field_path": path,
            "unit": unit,
            "period": row.get("period"),
            "page_no": int(row["page_no"]),
            "quote": str(row["quote"]),
            "confidence": 1.0,
            "extractor": "golden-truth/v1",
            "status": FactStatus.VALIDATED,
        }
        if row.get("value_numeric") is not None:
            payload["value_numeric"] = int(row["value_numeric"])
        else:
            payload["value_text"] = str(row["value_text"])
        facts.append(Fact(**payload))
    return tuple(facts)
