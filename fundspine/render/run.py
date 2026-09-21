"""Render partner commentaries and the IC memo from golden-validated facts."""

from __future__ import annotations

from pathlib import Path

from fundspine.config import settings
from fundspine.domain.enums import Tone
from fundspine.domain.models import Fact
from fundspine.drift.router import blocking
from fundspine.drift.rules import D101_restatement, D103_terms_change
from fundspine.drift.types import DriftFinding
from fundspine.render.binding import FactBinder, default_fmt, format_fact
from fundspine.render.document import render_ic_html, render_partner_html
from fundspine.render.from_golden import facts_from_golden
from fundspine.render.guard import validate_prose
from fundspine.render.markers import substitute_markers
from fundspine.render.partners import PARTNERS, PartnerConfig
from fundspine.render.plan import plan_ic_memo, plan_partner_commentary
from fundspine.render.prose import write_prose


def _display(finding: DriftFinding) -> dict[str, str]:
    return {
        "rule_id": finding.rule_id,
        "field_path": finding.field_path.value,
        "period": finding.period,
        "prior_display": format_fact(finding.prior_fact, default_fmt(finding.field_path)),
        "new_display": format_fact(finding.new_fact, default_fmt(finding.field_path)),
    }


def _finish_prose(raw: str, binder: FactBinder, disclosure: str) -> str:
    guarded = f"{raw} {disclosure}"
    violations = validate_prose(
        guarded,
        binder,
        disclosure=disclosure,
        allowed_fact_ids=binder.allowed_fact_ids(),
    )
    if violations:
        codes = ", ".join(v.code.value for v in violations)
        raise RuntimeError(f"guard refused prose: {codes}")
    return substitute_markers(raw, binder)


def _partner_html(partner: PartnerConfig, facts: tuple[Fact, ...], period: str) -> str:
    binder = FactBinder(facts)
    plan = plan_partner_commentary(period)
    raw = write_prose(partner.tone, facts, period)
    prose = _finish_prose(raw, binder, partner.disclosure)
    fund_name = binder.f("fund.name")
    return render_partner_html(
        partner=partner,
        plan=plan,
        binder=binder,
        prose=prose,
        fund_name=fund_name,
    )


def render_all(out_dir: Path | None = None) -> Path:
    dest = out_dir if out_dir is not None else settings().out_dir
    dest.mkdir(parents=True, exist_ok=True)
    q1 = facts_from_golden("doc_1")
    q3 = facts_from_golden("doc_3")
    findings = D101_restatement(q1, q3) + D103_terms_change(q1, q3)
    blocked = blocking(findings)

    for partner in PARTNERS:
        html = _partner_html(partner, q1, "2026Q1")
        (dest / f"{partner.slug}-2026Q1.html").write_text(html, encoding="utf-8")

    if blocked:
        lines = [
            "Partner commentary for 2026Q2 is refused.",
            "Open blocking drift:",
            *[
                (
                    f"- {item.rule_id}: {item.field_path.value} "
                    f"{format_fact(item.prior_fact, default_fmt(item.field_path))} -> "
                    f"{format_fact(item.new_fact, default_fmt(item.field_path))}"
                )
                for item in blocked
            ],
        ]
        reason = "\n".join(lines) + "\n"
        for partner in PARTNERS:
            (dest / f"{partner.slug}-2026Q2.blocked.txt").write_text(reason, encoding="utf-8")
    else:
        for partner in PARTNERS:
            html = _partner_html(partner, q3, "2026Q2")
            (dest / f"{partner.slug}-2026Q2.html").write_text(html, encoding="utf-8")

    ic_binder = FactBinder(q3)
    displays: list[dict[str, str]] = []
    for item in findings:
        displays.append(_display(item))
        ic_binder.used_fact_ids.append(item.prior_fact.fact_id)
        ic_binder.used_fact_ids.append(item.new_fact.fact_id)
    ic_plan = plan_ic_memo("2026Q2")
    ic_raw = write_prose(Tone.INSTITUTIONAL_TERSE, q3, "2026Q2")
    ic_disclosure = "Internal IC memorandum. Not for partner distribution while drift is open."
    ic_prose = _finish_prose(ic_raw, ic_binder, ic_disclosure)
    fund_name = ic_binder.f("fund.name")
    ic_html = render_ic_html(
        plan=ic_plan,
        binder=ic_binder,
        prose=ic_prose,
        fund_name=fund_name,
        findings=displays,
    )
    (dest / "ic-memo-2026Q2.html").write_text(ic_html, encoding="utf-8")
    print(f"wrote artifacts to {dest}")
    if blocked:
        print(f"blocked partner 2026Q2: {len(blocked)} drift event(s)")
    return dest
