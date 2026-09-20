"""LLM response schema. Values stay as written; conversion happens after."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LLMFact(BaseModel):
    field_path: str
    value_as_written: str
    page_no: int = Field(ge=1)
    quote: str = Field(min_length=3)
    period: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)


class LLMExtraction(BaseModel):
    facts: list[LLMFact]
