"""Inter-period detectors. Pure functions, no I/O."""

from __future__ import annotations

from collections.abc import Sequence

from fundspine.domain.enums import DriftKind, FieldPath, Severity
from fundspine.domain.models import Fact
from fundspine.drift.types import DriftFinding


def _numeric_index(facts: Sequence[Fact]) -> dict[tuple[FieldPath, str | None], Fact]:
    index: dict[tuple[FieldPath, str | None], Fact] = {}
    for fact in facts:
        if fact.value_numeric is None:
            continue
        index[(fact.field_path, fact.period)] = fact
    return index


def D101_restatement(prior: Sequence[Fact], incoming: Sequence[Fact]) -> list[DriftFinding]:
    """Same field, same period, different integer value → restatement."""
    old = _numeric_index(prior)
    new = _numeric_index(incoming)
    findings: list[DriftFinding] = []
    for key, new_fact in new.items():
        path, period = key
        if period is None:
            continue
        old_fact = old.get(key)
        if old_fact is None:
            continue
        if old_fact.value_numeric == new_fact.value_numeric:
            continue
        findings.append(
            DriftFinding(
                kind=DriftKind.RESTATEMENT,
                rule_id="D101_restatement",
                severity=Severity.BLOCK,
                period=period,
                field_path=path,
                prior_value=str(old_fact.value_numeric),
                new_value=str(new_fact.value_numeric),
                prior_fact=old_fact,
                new_fact=new_fact,
                hypotheses=(
                    "manager restated a previously reported figure",
                    "extractor bound the wrong cell on the later document",
                ),
            )
        )
    return findings


def D103_terms_change(prior: Sequence[Fact], incoming: Sequence[Fact]) -> list[DriftFinding]:
    """Standing economics that moved. Management fee is the headline case."""
    old = _numeric_index(prior)
    new = _numeric_index(incoming)
    path = FieldPath.TERMS_MGMT_FEE_BPS
    old_fact = old.get((path, None))
    new_fact = new.get((path, None))
    if old_fact is None or new_fact is None:
        return []
    if old_fact.value_numeric == new_fact.value_numeric:
        return []
    period = new_fact.period if new_fact.period is not None else "open"
    return [
        DriftFinding(
            kind=DriftKind.TERMS_CHANGE,
            rule_id="D103_terms_change",
            severity=Severity.BLOCK,
            period=period,
            field_path=path,
            prior_value=str(old_fact.value_numeric),
            new_value=str(new_fact.value_numeric),
            prior_fact=old_fact,
            new_fact=new_fact,
            hypotheses=(
                "terms changed effective a date named in the later document",
                "share-class mix-up between Class A rows",
            ),
        )
    ]
