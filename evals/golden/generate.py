"""Emit the three synthetic HTML documents and the truth files derived from them."""

from __future__ import annotations

import json
from pathlib import Path

from evals.golden import numbers as N
from evals.golden.doc_q2 import build_doc3
from evals.golden.docs import build_doc1, build_doc2
from evals.golden.format import TruthFact
from fundspine.ingest.loader import pages_from_html

GOLDEN_DIR = Path(__file__).resolve().parent


def _assert_quotes(html: str, facts: list[TruthFact], stem: str) -> None:
    pages = {page.page_no: page.text for page in pages_from_html(html)}
    for fact in facts:
        if fact.quote not in pages[fact.page_no]:
            raise ValueError(
                f"{stem}: quote for {fact.field_path} is not a substring of page "
                f"{fact.page_no}: {fact.quote!r}"
            )


def _write_doc(out_dir: Path, html: str, facts: list[TruthFact], meta: dict[str, str]) -> None:
    stem = meta["stem"]
    _assert_quotes(html, facts, stem)
    (out_dir / f"{stem}.html").write_text(html, encoding="utf-8")
    payload = {
        **meta,
        "facts": [
            {
                "field_path": f.field_path,
                "value_numeric": f.value_numeric,
                "value_text": f.value_text,
                "unit": f.unit,
                "period": f.period,
                "page_no": f.page_no,
                "quote": f.quote,
            }
            for f in facts
        ],
    }
    (out_dir / f"{stem}.truth.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def generate_all(out_dir: Path | None = None) -> Path:
    dest = out_dir if out_dir is not None else GOLDEN_DIR
    dest.mkdir(parents=True, exist_ok=True)
    fund = {
        "fund_id": N.FUND_ID,
        "name": N.FUND_NAME,
        "manager_name": N.MANAGER_NAME,
        "strategy_family": N.STRATEGY_FAMILY,
        "share_class": N.SHARE_CLASS,
        "currency": N.CURRENCY,
        "inception_date": N.INCEPTION.isoformat(),
        "firm_aum_usd_cents": N.FIRM_AUM_USD_CENTS,
    }
    (dest / "fund.json").write_text(json.dumps(fund, indent=2) + "\n", encoding="utf-8")
    for builder in (build_doc1, build_doc2, build_doc3):
        html, facts, meta = builder()
        _write_doc(dest, html, facts, meta)
    return dest


def main() -> None:
    dest = generate_all()
    print(f"wrote golden documents to {dest}")


if __name__ == "__main__":
    main()
