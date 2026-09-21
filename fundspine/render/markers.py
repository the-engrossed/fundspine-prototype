from __future__ import annotations

import re
from uuid import UUID

from fundspine.domain.ids import FactId
from fundspine.render.binding import FactBinder, UnboundFactError

MARKER = re.compile(r"\[\[fact:([0-9a-fA-F-]{36})\]\]")


def substitute_markers(prose: str, binder: FactBinder) -> str:
    """Replace [[fact:<uuid>]] with the bound formatted value."""

    def repl(match: re.Match[str]) -> str:
        fact_id = FactId(UUID(match.group(1)))
        return binder.formatted_id(fact_id)

    try:
        return MARKER.sub(repl, prose)
    except UnboundFactError:
        raise
