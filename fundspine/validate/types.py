from __future__ import annotations

from dataclasses import dataclass

from fundspine.domain.enums import FieldPath, Severity
from fundspine.domain.ids import FactId
from fundspine.domain.models import Fact, Period, Terms
from fundspine.ingest.loader import Page


@dataclass(frozen=True)
class RuleViolation:
    rule_id: str
    severity: Severity
    message: str
    hypotheses: tuple[str, ...]
    field_path: FieldPath | None = None
    fact_id: FactId | None = None


@dataclass(frozen=True)
class ValidationCtx:
    period: Period
    facts: tuple[Fact, ...]
    pages: tuple[Page, ...]
    terms: Terms | None
