"""Field-level scorecard. Pure: no database, no LLM."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fundspine.ingest.loader import Page

REQUIRED_PREFIXES = ("fund.", "metrics.", "terms.")


@dataclass(frozen=True)
class ExtractedField:
    field_path: str
    period: str | None
    value_numeric: int | None
    value_text: str | None
    page_no: int
    quote: str


def _key(field_path: str, period: str | None) -> tuple[str, str | None]:
    return (field_path, period)


def _is_required(field_path: str) -> bool:
    return any(field_path.startswith(prefix) for prefix in REQUIRED_PREFIXES)


@dataclass(frozen=True)
class DocScore:
    stem: str
    exact: dict[str, bool]
    recall: dict[str, bool]
    citation_valid: float
    extracted_count: int
    truth_count: int
    citation_hits: int


def score_document(
    *,
    stem: str,
    truth_facts: list[dict[str, Any]],
    extracted: list[ExtractedField],
    pages: tuple[Page, ...],
) -> DocScore:
    page_text = {page.page_no: page.text for page in pages}
    extracted_by_key = {_key(item.field_path, item.period): item for item in extracted}
    exact: dict[str, bool] = {}
    recall: dict[str, bool] = {}
    for fact in truth_facts:
        path = str(fact["field_path"])
        period = fact.get("period")
        period_s = str(period) if period is not None else None
        label = path if period_s is None else f"{path}@{period_s}"
        got = extracted_by_key.get(_key(path, period_s))
        recall[label] = got is not None
        if got is None:
            exact[label] = False
            continue
        if fact.get("value_numeric") is not None:
            exact[label] = got.value_numeric == fact["value_numeric"]
        else:
            exact[label] = got.value_text == fact.get("value_text")

    hits = 0
    for item in extracted:
        text = page_text.get(item.page_no, "")
        if item.quote and item.quote in text:
            hits += 1
    citation_valid = 1.0 if not extracted else hits / len(extracted)
    return DocScore(
        stem=stem,
        exact=exact,
        recall=recall,
        citation_valid=citation_valid,
        extracted_count=len(extracted),
        truth_count=len(truth_facts),
        citation_hits=hits,
    )


def required_recall(score: DocScore) -> float:
    keys = [key for key in score.recall if _is_required(key.split("@", 1)[0])]
    if not keys:
        raise RuntimeError(f"{score.stem}: no required fields in truth")
    return sum(1 for key in keys if score.recall[key]) / len(keys)


def render_scorecard(scores: list[DocScore]) -> str:
    lines = [
        "| doc | citation_validity | required_recall | exact_matches | extracted |",
        "|---|---|---|---|---|",
    ]
    for score in scores:
        exact_hits = sum(1 for ok in score.exact.values() if ok)
        lines.append(
            f"| {score.stem} | {score.citation_valid:.2%} | {required_recall(score):.2%} | "
            f"{exact_hits}/{score.truth_count} | {score.extracted_count} |"
        )
    return "\n".join(lines) + "\n"


def dump_scorecard(scores: list[DocScore], *, prompt_version: str) -> dict[str, Any]:
    """JSON shape for committed scorecard history and Loom diffs."""
    documents: list[dict[str, Any]] = []
    for score in scores:
        exact_hits = sum(1 for ok in score.exact.values() if ok)
        misses = [
            {
                "field": label,
                "recall": score.recall[label],
                "exact": score.exact[label],
            }
            for label in score.recall
            if not score.recall[label] or not score.exact[label]
        ]
        documents.append(
            {
                "stem": score.stem,
                "citation_validity": score.citation_valid,
                "required_recall": required_recall(score),
                "exact_matches": exact_hits,
                "truth_count": score.truth_count,
                "extracted_count": score.extracted_count,
                "citation_hits": score.citation_hits,
                "misses": misses,
                "recall": score.recall,
                "exact": score.exact,
            }
        )
    return {"prompt_version": prompt_version, "documents": documents}
