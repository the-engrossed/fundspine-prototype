"""Deterministic gate on model (or tone-template) prose.

G1 any bare digit in prose is a violation.
G2 every [[fact:uuid]] marker must parse and resolve.
G3 no marker may reference a fact outside this tenant's allowed set.
G4 disclosure block present verbatim.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from fundspine.domain.enums import FactStatus, GuardCode
from fundspine.domain.ids import FactId
from fundspine.render.binding import FactBinder
from fundspine.render.markers import MARKER


@dataclass(frozen=True)
class GuardViolation:
    code: GuardCode
    message: str


def validate_prose(
    prose: str,
    binder: FactBinder,
    *,
    disclosure: str,
    allowed_fact_ids: frozenset[FactId],
) -> list[GuardViolation]:
    """
    HAND-WRITTEN. Validates constrained LLM prose output against guard invariants.
    """
    violations: list[GuardViolation] = []

    # 1. G2 & G3: Check [[fact:<uuid>]] markers using typed FactId(UUID(...))
    found_markers = MARKER.findall(prose)
    for marker_str in found_markers:
        fact_id_raw = marker_str if isinstance(marker_str, str) else marker_str[0]

        # Parse string into FactId(UUID)
        try:
            fact_id = FactId(UUID(fact_id_raw))
        except (ValueError, TypeError):
            violations.append(
                GuardViolation(
                    code=GuardCode.BAD_MARKER,
                    message=f"Marker [[fact:{fact_id_raw}]] is not a valid UUID.",
                )
            )
            continue

        # Look up using typed fact_id
        fact = binder.fact_by_id(fact_id)

        # G2: Bad marker if not found or status is not VALIDATED
        if fact is None or getattr(fact, "status", None) != FactStatus.VALIDATED:
            violations.append(
                GuardViolation(
                    code=GuardCode.BAD_MARKER,
                    message=f"Marker [[fact:{fact_id_raw}]] does not resolve to a validated fact.",
                )
            )
            continue

        # G3: Cross tenant if resolved fact_id is not in the allowed set for this tenant
        if fact.fact_id not in allowed_fact_ids:
            violations.append(
                GuardViolation(
                    code=GuardCode.CROSS_TENANT,
                    message=f"Fact {fact.fact_id} belongs to another tenant/scope.",
                )
            )

    # 2. G1: UNBOUND_NUMERAL (strip valid markers first, check remaining text for digits)
    cleaned_prose = MARKER.sub("", prose)
    unbound_digits = re.findall(r"\d", cleaned_prose)
    if unbound_digits:
        violations.append(
            GuardViolation(
                code=GuardCode.UNBOUND_NUMERAL,
                message=(
                    f"Bare numerals detected in prose: {unbound_digits[:5]}. "
                    "Prose generator is strictly forbidden from emitting raw digits."
                ),
            )
        )

    # 3. G4: MISSING_DISCLOSURE
    if disclosure and disclosure.strip() not in prose:
        violations.append(
            GuardViolation(
                code=GuardCode.MISSING_DISCLOSURE,
                message="Partner disclosure block is missing or modified in generated output.",
            )
        )

    return violations
