from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from fundspine.render.binding import FactBinder
from fundspine.render.partners import PartnerConfig
from fundspine.render.plan import SectionPlan

_ENV = Environment(
    loader=FileSystemLoader(Path(__file__).resolve().parent / "templates"),
    autoescape=True,
    undefined=StrictUndefined,
)


def render_partner_html(
    *,
    partner: PartnerConfig,
    plan: SectionPlan,
    binder: FactBinder,
    prose: str,
    fund_name: str,
) -> str:
    template = _ENV.get_template("partner_commentary.html.j2")
    return template.render(
        partner=partner,
        plan=plan,
        f=binder.f,
        binder=binder,
        prose=prose,
        fund_name=fund_name,
        disclosure=partner.disclosure,
    )


def render_ic_html(
    *,
    plan: SectionPlan,
    binder: FactBinder,
    prose: str,
    fund_name: str,
    findings: Sequence[dict[str, str]],
) -> str:
    template = _ENV.get_template("ic_memo.html.j2")
    return template.render(
        plan=plan,
        f=binder.f,
        prose=prose,
        fund_name=fund_name,
        findings=findings,
        disclosure=(
            "Internal IC memorandum. Not for partner distribution while drift is open."
        ),
    )
