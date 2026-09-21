"""Spec for validate_prose. Fails until the hand-written body exists.

G1: after removing [[fact:<uuid>]] markers, any remaining digit is UNBOUND_NUMERAL.
    Hex inside a well-formed marker is not a violation — otherwise no marked
    sentence could pass.
G2: every [[fact:...]] marker must contain a UUID that binder.fact_by_id
    resolves to a VALIDATED fact.
G3: every resolved marker's fact_id must be in allowed_fact_ids.
G4: disclosure must appear in the prose string verbatim.
"""

from fundspine.domain.enums import FactStatus, GuardCode
from fundspine.domain.ids import new_fact_id
from fundspine.render.binding import FactBinder
from fundspine.render.guard import validate_prose
from tests.test_domain import make_fact


def _binder() -> tuple[FactBinder, object]:
    fact = make_fact(status=FactStatus.VALIDATED, value_numeric=347)
    return FactBinder([fact]), fact


def test_g1_any_digit_in_prose_is_a_violation() -> None:
    binder, fact = _binder()
    hits = validate_prose(
        f"Net return was [[fact:{fact.fact_id}]] in 2026.",
        binder,
        disclosure="Not an offer.",
        allowed_fact_ids=binder.allowed_fact_ids(),
    )
    assert any(v.code is GuardCode.UNBOUND_NUMERAL for v in hits)


def test_clean_marked_prose_with_disclosure_passes() -> None:
    binder, fact = _binder()
    disclosure = "Not an offer."
    prose = f"Net return was [[fact:{fact.fact_id}]]. {disclosure}"
    assert (
        validate_prose(
            prose,
            binder,
            disclosure=disclosure,
            allowed_fact_ids=binder.allowed_fact_ids(),
        )
        == []
    )


def test_g2_unknown_marker_is_a_violation() -> None:
    binder, _fact = _binder()
    ghost = new_fact_id()
    hits = validate_prose(
        f"Net return was [[fact:{ghost}]]. Not an offer.",
        binder,
        disclosure="Not an offer.",
        allowed_fact_ids=binder.allowed_fact_ids(),
    )
    assert any(v.code is GuardCode.BAD_MARKER for v in hits)


def test_g3_marker_outside_allowed_set_is_a_violation() -> None:
    binder, fact = _binder()
    hits = validate_prose(
        f"Net return was [[fact:{fact.fact_id}]]. Not an offer.",
        binder,
        disclosure="Not an offer.",
        allowed_fact_ids=frozenset(),
    )
    assert any(v.code is GuardCode.CROSS_TENANT for v in hits)


def test_g4_missing_disclosure_is_a_violation() -> None:
    binder, fact = _binder()
    hits = validate_prose(
        f"Net return was [[fact:{fact.fact_id}]]",
        binder,
        disclosure="Not an offer.",
        allowed_fact_ids=binder.allowed_fact_ids(),
    )
    assert any(v.code is GuardCode.MISSING_DISCLOSURE for v in hits)
