"""Pure validation rules. No I/O.

R001 is hand-written and left as a stub. R004 is deterministic citation check.
"""

from __future__ import annotations

from collections.abc import Callable

from fundspine.domain.enums import FieldPath, Severity
from fundspine.domain.models import Fact
from fundspine.validate.types import RuleViolation, ValidationCtx

RuleFn = Callable[[ValidationCtx], list[RuleViolation]]
RULES: dict[str, RuleFn] = {}


def rule(rule_id: str) -> Callable[[RuleFn], RuleFn]:
    def decorator(fn: RuleFn) -> RuleFn:
        RULES[rule_id] = fn
        return fn

    return decorator


def _value(facts: tuple[Fact, ...], path: FieldPath, period: str) -> Fact | None:
    matches = [
        fact
        for fact in facts
        if fact.field_path is path and fact.period == period and fact.value_numeric is not None
    ]
    return matches[0] if matches else None


@rule("R001_fee_bridge")
def R001_fee_bridge(ctx: ValidationCtx) -> list[RuleViolation]:
    """
    R001: Gross return minus quarterly management and performance fees must bridge to Net return.
    Uses terms in effect for the period, quarterly fee pro-rating, and a 2 bps tolerance.
    """
    period_label = ctx.period.label if hasattr(ctx.period, "label") else str(ctx.period)
    
    gross_fact = _value(ctx.facts, FieldPath.METRICS_GROSS_RETURN_BPS, period_label)
    net_fact = _value(ctx.facts, FieldPath.METRICS_NET_RETURN_BPS, period_label)

    if gross_fact is None or net_fact is None or ctx.terms is None:
        return []

    if gross_fact.value_numeric is None or net_fact.value_numeric is None:
        return []

    # Pro-rate annual terms to quarterly basis points using standard Python round()
    quarterly_mgmt = round(ctx.terms.mgmt_fee_bps / 4)
    quarterly_hurdle = round(ctx.terms.hurdle_bps / 4)

    # Performance fee applies to excess return above the quarterly hurdle
    excess_return = max(0, gross_fact.value_numeric - quarterly_hurdle)
    perf_fee = round((ctx.terms.perf_fee_bps / 10000.0) * excess_return)

    expected_net = gross_fact.value_numeric - quarterly_mgmt - perf_fee
    diff = abs(net_fact.value_numeric - expected_net)

    if diff > 2:  # 2 bps tolerance
        return [
            RuleViolation(
                rule_id="R001_fee_bridge",
                severity=Severity.BLOCK,
                field_path=net_fact.field_path,
                fact_id=net_fact.fact_id,
                message=(
                    f"R001 fee bridge violation: reported net {net_fact.value_numeric} bps "
                    f"differs from expected {expected_net} bps (diff: {diff} bps) "
                    f"given gross {gross_fact.value_numeric} bps, quarterly mgmt {quarterly_mgmt} bps, "  # noqa: E501
                    f"and performance fee {perf_fee} bps."
                ),
                hypotheses=(
                    "extraction error on gross or net return",
                    "source document is internally inconsistent (manager arithmetic error)",
                ),
            )
        ]

    return []

@rule("R004_citation_valid")
def R004_citation_valid(ctx: ValidationCtx) -> list[RuleViolation]:
    by_page = {page.page_no: page.text for page in ctx.pages}
    violations: list[RuleViolation] = []
    for fact in ctx.facts:
        text = by_page.get(fact.page_no)
        if text is None or fact.quote not in text:
            violations.append(
                RuleViolation(
                    rule_id="R004_citation_valid",
                    severity=Severity.BLOCK,
                    field_path=fact.field_path,
                    fact_id=fact.fact_id,
                    message=(
                        f"{fact.field_path}: quote {fact.quote!r} is not a substring "
                        f"of page {fact.page_no}"
                    ),
                    hypotheses=(
                        "extractor fabricated or truncated the quote",
                        "page text normalization dropped characters the quote still has",
                    ),
                )
            )
    return violations
