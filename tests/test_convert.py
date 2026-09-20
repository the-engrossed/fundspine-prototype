from fundspine.domain.enums import Unit
from fundspine.extract.convert import pct_to_bps, ratio_to_ratio_bps, to_integer, usd_to_cents


def test_percent_to_bps() -> None:
    assert pct_to_bps("4.50%") == 450
    assert pct_to_bps("20%") == 2000
    assert pct_to_bps("-11.50%") == -1150
    assert pct_to_bps("−11.50%") == -1150


def test_usd_to_cents() -> None:
    assert usd_to_cents("$128,430,000.00") == 12_843_000_000


def test_sharpe_to_ratio_bps() -> None:
    assert ratio_to_ratio_bps("1.42") == 14_200
    assert ratio_to_ratio_bps("1.42x") == 14_200


def test_to_integer_dispatches_on_unit() -> None:
    assert to_integer("12 months", Unit.MONTHS) == 12
    assert to_integer("90 days", Unit.DAYS) == 90
    assert to_integer("1.50%", Unit.BPS) == 150
