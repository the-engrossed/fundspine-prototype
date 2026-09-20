"""LLM structured extraction. Control flow is explicit; there is no agent loop."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from openai import OpenAI

from fundspine.config import settings
from fundspine.domain.ids import DocumentId, ExtractionRunId, FundId
from fundspine.domain.models import Fact
from fundspine.extract.materialize import DroppedFact, materialize_facts
from fundspine.extract.prompt import load_prompt
from fundspine.extract.schema import LLMExtraction
from fundspine.ingest.loader import Page


@dataclass(frozen=True)
class Extraction:
    facts: tuple[Fact, ...]
    dropped: tuple[DroppedFact, ...]
    tokens_in: int
    tokens_out: int
    model: str
    prompt_version: str


def assert_single_tenant(fund_id: FundId, pages: Sequence[Page]) -> None:
    """A prompt is an exfiltration surface: one fund, one payload."""
    if not pages:
        raise ValueError(f"extraction payload for fund {fund_id} is empty")


def _user_message(pages: Sequence[Page]) -> str:
    parts = [f"## Page {page.page_no}\n{page.text}" for page in pages]
    return "\n\n".join(parts)


def extract_document(
    *,
    fund_id: FundId,
    document_id: DocumentId,
    extraction_run_id: ExtractionRunId,
    pages: Sequence[Page],
) -> Extraction:
    assert_single_tenant(fund_id, tuple(pages))
    cfg = settings()
    prompt_version = cfg.prompt_version
    system = load_prompt(prompt_version, "extract")
    client = OpenAI(api_key=cfg.require_openai_key())
    completion = client.beta.chat.completions.parse(
        model=cfg.extract_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": _user_message(pages)},
        ],
        response_format=LLMExtraction,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError("extractor returned no parsed payload")
    usage = completion.usage
    tokens_in = 0 if usage is None else usage.prompt_tokens
    tokens_out = 0 if usage is None else usage.completion_tokens
    extractor_name = f"{cfg.extract_model}/{prompt_version}"
    facts, dropped = materialize_facts(
        parsed,
        fund_id=fund_id,
        document_id=document_id,
        extraction_run_id=extraction_run_id,
        extractor=extractor_name,
        pages=tuple(pages),
    )
    return Extraction(
        facts=facts,
        dropped=dropped,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        model=cfg.extract_model,
        prompt_version=prompt_version,
    )
