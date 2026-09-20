from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


def fmt_pct(bps: int) -> str:
    sign = "-" if bps < 0 else ""
    whole, frac = divmod(abs(bps), 100)
    return f"{sign}{whole}.{frac:02d}%"


def fmt_usd(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    dollars, rem = divmod(abs(cents), 100)
    return f"{sign}${dollars:,}.{rem:02d}"


def fmt_ratio(ratio_bps: int) -> str:
    value = Decimal(ratio_bps) / Decimal(10_000)
    return f"{value:.2f}"


def fmt_bps_rate(bps: int) -> str:
    """Annual fee/hurdle as a percent with two decimals, e.g. 150 → '1.50%'."""
    return fmt_pct(bps)


@dataclass
class TruthFact:
    field_path: str
    unit: str
    page_no: int
    quote: str
    value_numeric: int | None = None
    value_text: str | None = None
    period: str | None = None


@dataclass
class TruthRecorder:
    facts: list[TruthFact] = field(default_factory=list)

    def numeric(
        self,
        field_path: str,
        value: int,
        unit: str,
        page_no: int,
        quote: str,
        period: str | None,
    ) -> int:
        self.facts.append(
            TruthFact(
                field_path=field_path,
                value_numeric=value,
                unit=unit,
                page_no=page_no,
                quote=quote,
                period=period,
            )
        )
        return value

    def text(
        self,
        field_path: str,
        value: str,
        page_no: int,
        quote: str,
        period: str | None = None,
    ) -> str:
        self.facts.append(
            TruthFact(
                field_path=field_path,
                value_text=value,
                unit="text",
                page_no=page_no,
                quote=quote,
                period=period,
            )
        )
        return value
