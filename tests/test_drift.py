from fundspine.domain.enums import DriftKind, FieldPath, RoutingAction, Severity, Unit
from fundspine.drift.router import blocking, route
from fundspine.drift.rules import D101_restatement, D103_terms_change
from fundspine.render.from_golden import facts_from_golden
from tests.test_domain import make_fact


def test_d101_fires_when_the_same_period_nav_moves() -> None:
    prior = make_fact(
        field_path=FieldPath.METRICS_NAV_USD_CENTS,
        value_numeric=12_843_000_000,
        unit=Unit.USD_CENTS,
        period="2026Q1",
        quote="Net asset value at 31 March 2026 was $128,430,000.00.",
    )
    incoming = make_fact(
        field_path=FieldPath.METRICS_NAV_USD_CENTS,
        value_numeric=12_791_000_000,
        unit=Unit.USD_CENTS,
        period="2026Q1",
        quote=(
            "The previously reported 31 March 2026 NAV of $128,430,000.00 "
            "has been restated to $127,910,000.00."
        ),
    )
    hits = D101_restatement((prior,), (incoming,))
    assert len(hits) == 1
    assert hits[0].rule_id == "D101_restatement"
    assert hits[0].kind is DriftKind.RESTATEMENT
    assert route(hits[0]) is RoutingAction.BLOCK


def test_d101_is_silent_when_the_value_is_unchanged() -> None:
    fact = make_fact(
        field_path=FieldPath.METRICS_NAV_USD_CENTS,
        value_numeric=12_843_000_000,
        unit=Unit.USD_CENTS,
        quote="Net asset value at 31 March 2026 was $128,430,000.00.",
    )
    assert D101_restatement((fact,), (fact,)) == []


def test_d103_fires_when_the_management_fee_reprices() -> None:
    old = make_fact(
        field_path=FieldPath.TERMS_MGMT_FEE_BPS,
        value_numeric=150,
        unit=Unit.BPS,
        period=None,
        quote="Management fee 1.50% per annum.",
    )
    new = make_fact(
        field_path=FieldPath.TERMS_MGMT_FEE_BPS,
        value_numeric=175,
        unit=Unit.BPS,
        period=None,
        quote="Management fee 1.75% per annum effective 1 April 2026.",
    )
    hits = D103_terms_change((old,), (new,))
    assert len(hits) == 1
    assert hits[0].rule_id == "D103_terms_change"
    assert hits[0].severity is Severity.BLOCK


def test_golden_doc3_triggers_both_detectors() -> None:
    q1 = facts_from_golden("doc_1")
    q3 = facts_from_golden("doc_3")
    restated = D101_restatement(q1, q3)
    terms = D103_terms_change(q1, q3)
    assert any(item.field_path is FieldPath.METRICS_NAV_USD_CENTS for item in restated)
    assert terms[0].prior_value == "150"
    assert terms[0].new_value == "175"
    assert len(blocking(restated + terms)) >= 2
