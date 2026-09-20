from __future__ import annotations

from fundspine.validate.rules import RULES
from fundspine.validate.types import RuleViolation, ValidationCtx


def run_rules(ctx: ValidationCtx) -> tuple[RuleViolation, ...]:
    """Run every registered rule. Rules are pure; this function is too."""
    found: list[RuleViolation] = []
    for _rule_id, fn in RULES.items():
        found.extend(fn(ctx))
    return tuple(found)
