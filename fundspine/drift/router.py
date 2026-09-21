from __future__ import annotations

from collections.abc import Sequence

from fundspine.domain.enums import RoutingAction, Severity
from fundspine.drift.types import DriftFinding


def route(finding: DriftFinding) -> RoutingAction:
    if finding.severity is Severity.BLOCK:
        return RoutingAction.BLOCK
    if finding.severity is Severity.REVIEW:
        return RoutingAction.REVIEW
    return RoutingAction.ACK


def blocking(findings: Sequence[DriftFinding]) -> tuple[DriftFinding, ...]:
    return tuple(item for item in findings if route(item) is RoutingAction.BLOCK)
