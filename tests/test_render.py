import pytest

from fundspine.domain.enums import FactStatus, Tone
from fundspine.render.binding import FactBinder, UnboundFactError
from fundspine.render.from_golden import facts_from_golden
from fundspine.render.markers import MARKER, substitute_markers
from fundspine.render.partners import APEX, RIDGELINE
from fundspine.render.prose import write_prose
from fundspine.render.run import render_all
from tests.test_domain import make_fact


def test_write_prose_has_no_digits_outside_markers() -> None:
    facts = facts_from_golden("doc_1")
    prose = write_prose(Tone.ADVISORY_WARM, facts, "2026Q1")
    stripped = MARKER.sub("", prose)
    assert not any(ch.isdigit() for ch in stripped)
    assert "forty" in prose


def test_substitute_markers_inserts_the_formatted_figure() -> None:
    fact = make_fact(status=FactStatus.VALIDATED, value_numeric=347)
    binder = FactBinder([fact])
    rendered = substitute_markers(f"Net was [[fact:{fact.fact_id}]].", binder)
    assert rendered == "Net was 3.47%."


def test_substitute_unknown_marker_fails_loudly() -> None:
    binder = FactBinder([])
    with pytest.raises(UnboundFactError):
        substitute_markers("Net was [[fact:00000000-0000-0000-0000-000000000000]].", binder)


def test_render_all_writes_two_partner_q1_docs_and_blocks_q2(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("fundspine.render.run.validate_prose", lambda *a, **k: [])
    dest = render_all(tmp_path)
    apex = (dest / "apex-2026Q1.html").read_text(encoding="utf-8")
    ridge = (dest / "ridgeline-2026Q1.html").read_text(encoding="utf-8")
    assert APEX.name in apex
    assert RIDGELINE.name in ridge
    assert "3.47%" in apex
    assert "3.47%" in ridge
    assert "$128,430,000.00" in apex
    assert "$128,430,000.00" in ridge
    assert "forty liquid futures" in apex
    assert "Futures-only book" in ridge
    assert "Net return for the quarter was 3.47%." in apex
    assert not (dest / "apex-2026Q2.html").exists()
    blocked = (dest / "apex-2026Q2.blocked.txt").read_text(encoding="utf-8")
    assert "refused" in blocked
    assert "D101_restatement" in blocked
    assert "D103_terms_change" in blocked
    ic = (dest / "ic-memo-2026Q2.html").read_text(encoding="utf-8")
    assert "$127,910,000.00" in ic
    assert "$128,430,000.00" in ic
    assert "1.75%" in ic
    assert "1.50%" in ic
