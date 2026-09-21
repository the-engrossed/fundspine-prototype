import pytest

from fundspine.domain.enums import FactStatus, FieldPath, Unit
from fundspine.render.binding import FactBinder, UnboundFactError
from tests.test_domain import make_fact


def _validated(**overrides: object):
    return make_fact(status=FactStatus.VALIDATED, **overrides)


def test_f_formats_bps_as_percent() -> None:
    fact = _validated(value_numeric=347)
    binder = FactBinder([fact])
    assert binder.f("metrics.net_return_bps") == "3.47%"
    assert binder.used_fact_ids == [fact.fact_id]


def test_f_formats_money_and_sharpe() -> None:
    nav = _validated(
        field_path=FieldPath.METRICS_NAV_USD_CENTS,
        value_numeric=12_843_000_000,
        unit=Unit.USD_CENTS,
        quote="Net asset value at 31 March 2026 was $128,430,000.00.",
    )
    sharpe = _validated(
        field_path=FieldPath.METRICS_SHARPE_36M,
        value_numeric=14_200,
        unit=Unit.RATIO_BPS,
        quote="The thirty-six month Sharpe ratio was 1.42.",
    )
    binder = FactBinder([nav, sharpe])
    assert binder.f("metrics.nav_usd_cents", fmt="usd") == "$128,430,000.00"
    assert binder.f("metrics.sharpe_36m", fmt="ratio") == "1.42"


def test_candidate_facts_do_not_bind() -> None:
    fact = make_fact()
    binder = FactBinder([fact])
    with pytest.raises(UnboundFactError, match="metrics.net_return_bps"):
        binder.f("metrics.net_return_bps")


def test_missing_path_fails_loudly() -> None:
    binder = FactBinder([])
    with pytest.raises(UnboundFactError, match="metrics.gross_return_bps"):
        binder.f("metrics.gross_return_bps")


def test_ambiguous_path_without_period_fails_loudly() -> None:
    q1 = _validated(
        value_numeric=347,
        period="2026Q1",
        quote="Net return for the quarter was 3.47%.",
    )
    q2 = _validated(
        value_numeric=157,
        period="2026Q2",
        quote="Net return for the quarter was 1.57%.",
    )
    binder = FactBinder([q1, q2])
    with pytest.raises(UnboundFactError, match="ambiguous"):
        binder.f("metrics.net_return_bps")
    assert binder.f("metrics.net_return_bps", period="2026Q1") == "3.47%"
