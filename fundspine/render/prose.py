"""Deterministic prose. Tone is an enum mapped to a fixed sentence pair.

No LLM: billing is not a render dependency. Numbers enter only as [[fact:uuid]].
"""

from __future__ import annotations

from collections.abc import Sequence

from fundspine.domain.enums import FieldPath, Tone
from fundspine.domain.models import Fact


def _one(facts: Sequence[Fact], path: FieldPath, period: str) -> Fact:
    matches = [fact for fact in facts if fact.field_path is path and fact.period == period]
    if len(matches) != 1:
        terms = [fact for fact in facts if fact.field_path is path]
        if path.value.startswith("terms.") and len(terms) == 1:
            return terms[0]
        raise RuntimeError(f"prose expected one fact for {path.value} in {period}")
    return matches[0]


def _m(fact: Fact) -> str:
    return f"[[fact:{fact.fact_id}]]"


def write_prose(tone: Tone, facts: Sequence[Fact], period: str) -> str:
    net = _one(facts, FieldPath.METRICS_NET_RETURN_BPS, period)
    gross = _one(facts, FieldPath.METRICS_GROSS_RETURN_BPS, period)
    mgmt = _one(facts, FieldPath.TERMS_MGMT_FEE_BPS, period)
    if tone is Tone.ADVISORY_WARM:
        return (
            f"We closed the quarter with a net return of {_m(net)}, "
            f"against a gross return of {_m(gross)} and the management fee of {_m(mgmt)} "
            "then in force. The programme continues to express itself through forty "
            "liquid futures markets rather than a concentrated cash-equity book."
        )
    if tone is Tone.INSTITUTIONAL_TERSE:
        return (
            f"Net {_m(net)}. Gross {_m(gross)}. Management fee {_m(mgmt)} in force for the period. "
            "Futures-only book. No discretionary overlay."
        )
    raise ValueError(f"unsupported tone {tone}")
