"""Domain invariants.

These tests are the specification for the two hand-written validators in
fundspine/domain/models.py. They are written first and they fail until those
validator bodies exist.
"""

from datetime import date

import pytest
from pydantic import ValidationError

from fundspine.domain.enums import FactStatus, FieldPath, Unit
from fundspine.domain.ids import (
    new_document_id,
    new_extraction_run_id,
    new_fact_id,
    new_fund_id,
    new_terms_id,
)
from fundspine.domain.models import Fact, FundPeriodMetrics, Period, Terms

FUND = new_fund_id()
DOC = new_document_id()
RUN = new_extraction_run_id()


def make_fact(**overrides: object) -> Fact:
    payload: dict[str, object] = {
        "fact_id": new_fact_id(),
        "fund_id": FUND,
        "document_id": DOC,
        "extraction_run_id": RUN,
        "field_path": FieldPath.METRICS_NET_RETURN_BPS,
        "value_numeric": 412,
        "unit": Unit.BPS,
        "period": "2026Q1",
        "page_no": 1,
        "quote": "Net return for the quarter was 4.12%.",
        "confidence": 0.94,
        "extractor": "gpt-4o/v1",
    }
    payload.update(overrides)
    return Fact(**payload)  # type: ignore[arg-type]


class TestFactInvariants:
    def test_numeric_fact_constructs(self) -> None:
        fact = make_fact()
        assert fact.value_numeric == 412
        assert fact.value_text is None
        assert fact.status is FactStatus.CANDIDATE

    def test_text_fact_constructs(self) -> None:
        fact = make_fact(
            field_path=FieldPath.NARRATIVE_STRATEGY,
            value_numeric=None,
            value_text="Systematic global macro across liquid futures.",
            unit=Unit.TEXT,
        )
        assert fact.value_text is not None
        assert fact.value_numeric is None

    def test_both_values_set_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            make_fact(value_text="also text")

    def test_neither_value_set_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            make_fact(value_numeric=None)

    def test_unit_must_match_the_field_path(self) -> None:
        with pytest.raises(ValidationError):
            make_fact(field_path=FieldPath.METRICS_NAV_USD_CENTS, unit=Unit.BPS)

    def test_text_unit_requires_text_value(self) -> None:
        with pytest.raises(ValidationError):
            make_fact(field_path=FieldPath.NARRATIVE_STRATEGY, unit=Unit.TEXT, value_numeric=7)

    def test_numeric_unit_rejects_text_value(self) -> None:
        with pytest.raises(ValidationError):
            make_fact(value_numeric=None, value_text="four point one two percent")

    def test_superseded_by_requires_superseded_status(self) -> None:
        with pytest.raises(ValidationError):
            make_fact(superseded_by=new_fact_id())

    def test_superseded_status_requires_superseded_by(self) -> None:
        with pytest.raises(ValidationError):
            make_fact(status=FactStatus.SUPERSEDED)

    def test_supersede_pair_is_accepted(self) -> None:
        fact = make_fact(status=FactStatus.SUPERSEDED, superseded_by=new_fact_id())
        assert fact.superseded_by is not None

    def test_a_fact_without_a_usable_quote_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            make_fact(quote="")

    def test_page_numbers_start_at_one(self) -> None:
        with pytest.raises(ValidationError):
            make_fact(page_no=0)

    def test_confidence_is_bounded(self) -> None:
        with pytest.raises(ValidationError):
            make_fact(confidence=1.4)

    def test_facts_are_immutable(self) -> None:
        fact = make_fact()
        with pytest.raises(ValidationError):
            fact.value_numeric = 999  # type: ignore[misc]

    def test_financial_values_are_never_floats(self) -> None:
        """A float that happens to be integral is still a float at the boundary."""
        fact = make_fact(value_numeric=412)
        assert isinstance(fact.value_numeric, int)
        assert not isinstance(fact.value_numeric, float)


class TestMetricPairing:
    def test_value_with_fact_id_is_accepted(self) -> None:
        metrics = FundPeriodMetrics(
            fund_id=FUND,
            period="2026Q1",
            net_return_bps=412,
            net_return_bps_fact_id=new_fact_id(),
        )
        assert metrics.net_return_bps == 412

    def test_all_empty_is_accepted(self) -> None:
        metrics = FundPeriodMetrics(fund_id=FUND, period="2026Q1")
        assert metrics.bound_fact_ids() == []

    def test_value_without_fact_id_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            FundPeriodMetrics(fund_id=FUND, period="2026Q1", net_return_bps=412)

    def test_fact_id_without_value_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            FundPeriodMetrics(fund_id=FUND, period="2026Q1", nav_usd_cents_fact_id=new_fact_id())

    def test_the_error_names_the_offending_pair(self) -> None:
        with pytest.raises(ValidationError, match="sharpe_36m"):
            FundPeriodMetrics(fund_id=FUND, period="2026Q1", sharpe_36m=14_200)

    def test_pairing_is_checked_for_every_metric_not_just_the_first(self) -> None:
        with pytest.raises(ValidationError, match="max_drawdown_bps"):
            FundPeriodMetrics(
                fund_id=FUND,
                period="2026Q1",
                net_return_bps=412,
                net_return_bps_fact_id=new_fact_id(),
                max_drawdown_bps=-1_150,
            )

    def test_bound_fact_ids_is_the_provenance_set(self) -> None:
        net, nav = new_fact_id(), new_fact_id()
        metrics = FundPeriodMetrics(
            fund_id=FUND,
            period="2026Q1",
            net_return_bps=412,
            net_return_bps_fact_id=net,
            nav_usd_cents=1_284_300_00,
            nav_usd_cents_fact_id=nav,
        )
        assert metrics.bound_fact_ids() == [net, nav]

    def test_pairing_is_derived_not_hand_listed(self) -> None:
        """Every value field must have a partner fact_id field declared.

        This is what stops a new metric from shipping without provenance.
        """
        names = set(FundPeriodMetrics.model_fields)
        value_fields = {
            n for n in names if not n.endswith("_fact_id") and n not in {"fund_id", "period"}
        }
        assert {f"{n}_fact_id" for n in value_fields} <= names


class TestTerms:
    def make_terms(self, **overrides: object) -> Terms:
        payload: dict[str, object] = {
            "terms_id": new_terms_id(),
            "fund_id": FUND,
            "mgmt_fee_bps": 150,
            "perf_fee_bps": 2_000,
            "hurdle_bps": 500,
            "high_water_mark": True,
            "lockup_months": 12,
            "notice_days": 90,
            "effective_from": date(2018, 3, 1),
        }
        payload.update(overrides)
        return Terms(**payload)  # type: ignore[arg-type]

    def test_open_ended_terms_cover_any_later_day(self) -> None:
        terms = self.make_terms()
        assert terms.covers(date(2026, 3, 31))

    def test_terms_do_not_cover_days_before_they_took_effect(self) -> None:
        terms = self.make_terms(effective_from=date(2026, 4, 1))
        assert not terms.covers(date(2026, 3, 31))

    def test_the_interval_is_half_open(self) -> None:
        terms = self.make_terms(effective_to=date(2026, 4, 1))
        assert terms.covers(date(2026, 3, 31))
        assert not terms.covers(date(2026, 4, 1))

    def test_inverted_range_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            self.make_terms(effective_from=date(2026, 4, 1), effective_to=date(2026, 1, 1))

    def test_a_q2_memo_resolves_the_fee_in_force_during_q2(self) -> None:
        """The reason terms exist as a table at all."""
        old = self.make_terms(mgmt_fee_bps=150, effective_to=date(2026, 4, 1))
        new = self.make_terms(mgmt_fee_bps=175, effective_from=date(2026, 4, 1))
        q2_start = Period(year=2026, quarter=2).start
        in_force = [t for t in (old, new) if t.covers(q2_start)]
        assert [t.mgmt_fee_bps for t in in_force] == [175]


class TestPeriod:
    def test_quarter_boundaries(self) -> None:
        q1 = Period(year=2026, quarter=1)
        assert q1.start == date(2026, 1, 1)
        assert q1.end == date(2026, 4, 1)

    def test_q4_rolls_the_year(self) -> None:
        assert Period(year=2026, quarter=4).end == date(2027, 1, 1)

    def test_periods_order(self) -> None:
        assert Period(year=2026, quarter=1) < Period(year=2026, quarter=2)

    def test_label_round_trips(self) -> None:
        assert Period.parse("2026Q2").label == "2026Q2"
