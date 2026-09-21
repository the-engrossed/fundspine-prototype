from __future__ import annotations

from dataclasses import dataclass

from fundspine.domain.enums import DriftKind, FieldPath, Severity
from fundspine.domain.models import Fact


@dataclass(frozen=True)
class DriftFinding:
    kind: DriftKind
    rule_id: str
    severity: Severity
    period: str
    field_path: FieldPath
    prior_value: str
    new_value: str
    prior_fact: Fact
    new_fact: Fact
    hypotheses: tuple[str, ...]
