"""Spec for R001 (hand-written) and R004 (citation)."""

from datetime import date

from fundspine.domain.enums import FieldPath, Severity, Unit
from fundspine.domain.ids import new_terms_id
from fundspine.domain.models import Period, Terms
from fundspine.ingest.loader import Page
from fundspine.validate.rules import R001_fee_bridge, R004_citation_valid
from fundspine.validate.types import ValidationCtx
from tests.test_domain import FUND, make_fact


def _terms(*, mgmt: int = 150) -> Terms:
    return Terms(
        terms_id=new_terms_id(),
        fund_id=FUND,
        mgmt_fee_bps=mgmt,
        perf_fee_bps=2_000,
        hurdle_bps=500,
        high_water_mark=True,
        lockup_months=12,
        notice_days=90,
        effective_from=date(2018, 3, 1),
    )


def _q1_facts(*, net: int) -> tuple:
    return (
        make_fact(
            field_path=FieldPath.METRICS_GROSS_RETURN_BPS,
            value_numeric=450,
            unit=Unit.BPS,
            period="2026Q1",
            quote="Gross return for the quarter was 4.50%.",
        ),
        make_fact(
            field_path=FieldPath.METRICS_NET_RETURN_BPS,
            value_numeric=net,
            unit=Unit.BPS,
            period="2026Q1",
            quote="Net return for the quarter was 3.47%."
            if net == 347
            else "Net return for the quarter was 3.87%.",
        ),
    )


def test_r004_accepts_a_verbatim_quote() -> None:
    fact = make_fact(quote="Net return for the quarter was 3.55%.")
    ctx = ValidationCtx(
        period=Period(year=2026, quarter=1),
        facts=(fact,),
        pages=(Page(page_no=1, text="Net return for the quarter was 3.55%."),),
        terms=None,
    )
    assert R004_citation_valid(ctx) == []


def test_r004_rejects_a_quote_not_on_the_page() -> None:
    fact = make_fact(quote="Net return for the quarter was 3.55%.")
    ctx = ValidationCtx(
        period=Period(year=2026, quarter=1),
        facts=(fact,),
        pages=(Page(page_no=1, text="something else entirely sits here."),),
        terms=None,
    )
    hits = R004_citation_valid(ctx)
    assert len(hits) == 1
    assert hits[0].rule_id == "R004_citation_valid"
    assert hits[0].severity is Severity.BLOCK


def test_r001_passes_when_the_bridge_closes() -> None:
    ctx = ValidationCtx(
        period=Period(year=2026, quarter=1),
        facts=_q1_facts(net=347),
        pages=(Page(page_no=1, text="Gross return for the quarter was 4.50%."),),
        terms=_terms(),
    )
    assert R001_fee_bridge(ctx) == []


def test_r001_fires_when_net_is_forty_bps_off() -> None:
    ctx = ValidationCtx(
        period=Period(year=2026, quarter=1),
        facts=_q1_facts(net=387),
        pages=(Page(page_no=1, text="Gross return for the quarter was 4.50%."),),
        terms=_terms(),
    )
    hits = R001_fee_bridge(ctx)
    assert len(hits) == 1
    assert hits[0].rule_id == "R001_fee_bridge"
    assert hits[0].severity is Severity.BLOCK


def test_r001_uses_terms_in_force_not_a_constant() -> None:
    """175 bps annual → quarterly 44; Q2 numbers close the bridge."""
    facts = (
        make_fact(
            field_path=FieldPath.METRICS_GROSS_RETURN_BPS,
            value_numeric=220,
            unit=Unit.BPS,
            period="2026Q2",
            quote="Gross return for the quarter was 2.20%.",
        ),
        make_fact(
            field_path=FieldPath.METRICS_NET_RETURN_BPS,
            value_numeric=157,
            unit=Unit.BPS,
            period="2026Q2",
            quote="Net return for the quarter was 1.57%.",
        ),
    )
    ctx = ValidationCtx(
        period=Period(year=2026, quarter=2),
        facts=facts,
        pages=(Page(page_no=1, text="Gross return for the quarter was 2.20%."),),
        terms=_terms(mgmt=175),
    )
    assert R001_fee_bridge(ctx) == []
