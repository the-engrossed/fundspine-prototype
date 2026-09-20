"""Resolve field paths to formatted values and record provenance.

Every number that reaches a document goes through f(). There is no other door.
"""

from __future__ import annotations

from decimal import Decimal

from fundspine.domain.enums import FactStatus, FieldPath, Unit
from fundspine.domain.ids import FactId
from fundspine.domain.models import Fact


class UnboundFactError(RuntimeError):
    """Raised when a template asks for a figure that is not a validated fact."""


def _pct(bps: int) -> str:
    sign = "-" if bps < 0 else ""
    whole, frac = divmod(abs(bps), 100)
    return f"{sign}{whole}.{frac:02d}%"


def _usd(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    dollars, rem = divmod(abs(cents), 100)
    return f"{sign}${dollars:,}.{rem:02d}"


def _ratio(ratio_bps: int) -> str:
    value = Decimal(ratio_bps) / Decimal(10_000)
    return f"{value:.2f}"


def format_fact(fact: Fact, fmt: str) -> str:
    if fact.unit is Unit.TEXT:
        if fact.value_text is None:
            raise UnboundFactError(f"{fact.field_path} has no text value")
        return fact.value_text
    if fact.value_numeric is None:
        raise UnboundFactError(f"{fact.field_path} has no numeric value")
    if fmt == "pct2":
        return _pct(fact.value_numeric)
    if fmt == "usd":
        return _usd(fact.value_numeric)
    if fmt == "ratio":
        return _ratio(fact.value_numeric)
    if fmt == "int":
        return str(fact.value_numeric)
    raise ValueError(f"unknown format {fmt!r}")


class FactBinder:
    """Jinja global f(). Appends each resolved fact_id to used_fact_ids."""

    def __init__(self, facts: dict[FieldPath, Fact]) -> None:
        self._facts = facts
        self.used_fact_ids: list[FactId] = []

    def f(self, field_path: str, *, fmt: str = "pct2") -> str:
        try:
            path = FieldPath(field_path)
        except ValueError as exc:
            raise UnboundFactError(f"unknown field path {field_path!r}") from exc
        fact = self._facts.get(path)
        if fact is None or fact.status is not FactStatus.VALIDATED:
            raise UnboundFactError(f"no validated fact for {field_path}")
        rendered = format_fact(fact, fmt)
        self.used_fact_ids.append(fact.fact_id)
        return rendered
