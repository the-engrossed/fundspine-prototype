"""Integer conversion at the extraction boundary. Nowhere else."""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal

from fundspine.domain.enums import Unit

_MINUS = str.maketrans({"−": "-", "–": "-", "—": "-"})
_MONEY = re.compile(r"[^0-9.\-]")
_COUNT = re.compile(r"-?\d+")


class ConversionError(ValueError):
    pass


def _decimal(text: str) -> Decimal:
    cleaned = text.translate(_MINUS).strip().replace(",", "")
    cleaned = cleaned.replace("%", "").replace("$", "").rstrip("xX")
    cleaned = cleaned.replace(" ", "")
    if not cleaned or cleaned in {".", "-", "-."}:
        raise ConversionError(f"not a number: {text!r}")
    try:
        return Decimal(cleaned)
    except Exception as exc:
        raise ConversionError(f"not a number: {text!r}") from exc


def _to_int(value: Decimal, scale: int) -> int:
    scaled = (value * Decimal(scale)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(scaled)


def pct_to_bps(text: str) -> int:
    """'4.50%' or '4.50' → 450. '20%' → 2000."""
    return _to_int(_decimal(text), 100)


def usd_to_cents(text: str) -> int:
    """'$128,430,000.00' → 12843000000."""
    cleaned = text.translate(_MINUS).strip()
    cleaned = _MONEY.sub("", cleaned.replace(",", ""))
    if not cleaned:
        raise ConversionError(f"not money: {text!r}")
    return _to_int(Decimal(cleaned), 100)


def ratio_to_ratio_bps(text: str) -> int:
    """'1.42' or '1.42x' → 14200."""
    return _to_int(_decimal(text), 10_000)


def count_to_int(text: str) -> int:
    """'12 months' / '90 days' / '12' → 12."""
    match = _COUNT.search(text.translate(_MINUS))
    if match is None:
        raise ConversionError(f"not a count: {text!r}")
    return int(match.group(0))


def to_integer(value_as_written: str, unit: Unit) -> int:
    if unit is Unit.BPS:
        return pct_to_bps(value_as_written)
    if unit is Unit.USD_CENTS:
        return usd_to_cents(value_as_written)
    if unit is Unit.RATIO_BPS:
        return ratio_to_ratio_bps(value_as_written)
    if unit in {Unit.MONTHS, Unit.DAYS}:
        return count_to_int(value_as_written)
    raise ConversionError(f"unit {unit} is not numeric")
