from __future__ import annotations

from dataclasses import dataclass

from fundspine.domain.enums import Tone


@dataclass(frozen=True)
class PartnerConfig:
    slug: str
    name: str
    tone: Tone
    accent: str
    paper: str
    disclosure: str
    jurisdiction: str


APEX = PartnerConfig(
    slug="apex",
    name="Apex Wealth Partners",
    tone=Tone.ADVISORY_WARM,
    accent="#1f4e79",
    paper="#f4f7fb",
    disclosure=(
        "This commentary is prepared solely for clients of Apex Wealth Partners. "
        "It is not an offer to sell securities and it is not investment advice "
        "for any person other than the named recipient."
    ),
    jurisdiction="US",
)

RIDGELINE = PartnerConfig(
    slug="ridgeline",
    name="Ridgeline Family Office",
    tone=Tone.INSTITUTIONAL_TERSE,
    accent="#4a5560",
    paper="#f6f6f4",
    disclosure=(
        "Prepared for Ridgeline Family Office. Confidential. Not an offer. "
        "Figures are bound to cited facts in the appendix; do not circulate."
    ),
    jurisdiction="US",
)

PARTNERS: tuple[PartnerConfig, ...] = (APEX, RIDGELINE)
