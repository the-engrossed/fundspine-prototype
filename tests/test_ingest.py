from pathlib import Path

import pytest

from fundspine.ingest.loader import load_html_file, parse_html, sha256_hex


def test_pages_split_on_section_and_tables_are_linearized() -> None:
    html = """
    <html><body>
      <section class="page" data-page-no="1">
        <h1>Cover</h1>
        <table>
          <tr><th>Period</th><th>Return</th></tr>
          <tr><td>Q1 2026</td><td>4.50%</td></tr>
        </table>
      </section>
      <section class="page" data-page-no="2">
        <p>Net return for the quarter was 3.55%.</p>
      </section>
    </body></html>
    """
    parsed = parse_html(html, source_uri="memory://fixture")
    assert parsed.page_count == 2
    assert "4.50%" in parsed.text_for(1)
    assert "Q1 2026 | 4.50%" in parsed.text_for(1) or "4.50%" in parsed.text_for(1)
    assert "Net return for the quarter was 3.55%." in parsed.text_for(2)


def test_missing_page_sections_fail_loudly() -> None:
    with pytest.raises(ValueError, match="no <section"):
        parse_html("<html><p>no pages</p></html>", source_uri="memory://bad")


def test_non_contiguous_pages_fail_loudly() -> None:
    html = """
    <section class="page" data-page-no="1"><p>one</p></section>
    <section class="page" data-page-no="3"><p>three</p></section>
    """
    with pytest.raises(ValueError, match="contiguous"):
        parse_html(html, source_uri="memory://gap")


def test_sha256_is_stable_and_file_load_round_trips(tmp_path: Path) -> None:
    html = (
        '<section class="page" data-page-no="1"><p>Meridian Systematic Macro Fund</p>'
        "</section>"
    )
    path = tmp_path / "doc.html"
    path.write_text(html, encoding="utf-8")
    loaded = load_html_file(path)
    assert loaded.sha256 == sha256_hex(html.encode("utf-8"))
    assert loaded.pages[0].text == "Meridian Systematic Macro Fund"
    again = load_html_file(path)
    assert again.sha256 == loaded.sha256
