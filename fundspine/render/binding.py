"""Resolve field paths to formatted values and record provenance.

Every number that reaches a document goes through f(). There is no other door.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

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


def default_fmt(path: FieldPath) -> str:
    if path is FieldPath.METRICS_NAV_USD_CENTS:
        return "usd"
    if path is FieldPath.METRICS_SHARPE_36M:
        return "ratio"
    if path in {FieldPath.TERMS_LOCKUP_MONTHS, FieldPath.TERMS_NOTICE_DAYS}:
        return "int"
    if path in {
        FieldPath.FUND_NAME,
        FieldPath.FUND_MANAGER_NAME,
        FieldPath.FUND_STRATEGY_FAMILY,
        FieldPath.FUND_SHARE_CLASS,
        FieldPath.NARRATIVE_STRATEGY,
    }:
        return "pct2"  # unused; text facts ignore fmt
    return "pct2"


class FactBinder:
    """Jinja global f(). Appends each resolved fact_id to used_fact_ids."""

    def __init__(self, facts: Sequence[Fact]) -> None:
        self._facts = tuple(facts)
        self.used_fact_ids: list[FactId] = []

    def allowed_fact_ids(self) -> frozenset[FactId]:
        return frozenset(fact.fact_id for fact in self._facts)

    def fact_by_id(self, fact_id: FactId | UUID) -> Fact | None:
        for fact in self._facts:
            if fact.fact_id == fact_id:
                return fact
        return None

    def _get(self, path: FieldPath, period: str | None) -> Fact:
        matches = [
            fact
            for fact in self._facts
            if fact.field_path is path and fact.status is FactStatus.VALIDATED
        ]
        if period is not None:
            matches = [fact for fact in matches if fact.period == period]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise UnboundFactError(f"no validated fact for {path.value}")
        raise UnboundFactError(f"ambiguous fact for {path.value} period={period}")

    def f(self, field_path: str, *, fmt: str | None = None, period: str | None = None) -> str:
        try:
            path = FieldPath(field_path)
        except ValueError as exc:
            raise UnboundFactError(f"unknown field path {field_path!r}") from exc
        fact = self._get(path, period)
        rendered = format_fact(fact, fmt if fmt is not None else default_fmt(path))
        self.used_fact_ids.append(fact.fact_id)
        return rendered

    def formatted_id(self, fact_id: FactId | UUID) -> str:
        fact = self.fact_by_id(fact_id)
        if fact is None or fact.status is not FactStatus.VALIDATED:
            raise UnboundFactError(f"no validated fact {fact_id}")
        rendered = format_fact(fact, default_fmt(fact.field_path))
        self.used_fact_ids.append(fact.fact_id)
        return rendered

    def display(self, fact: Fact) -> str:
        return format_fact(fact, default_fmt(fact.field_path))

    def provenance(self) -> list[Fact]:
        seen: set[FactId] = set()
        rows: list[Fact] = []
        for fact_id in self.used_fact_ids:
            if fact_id in seen:
                continue
            seen.add(fact_id)
            fact = self.fact_by_id(fact_id)
            if fact is not None:
                rows.append(fact)
        return rows
