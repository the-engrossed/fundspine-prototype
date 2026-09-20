"""Deterministic HTML table linearization.

Tag-stripping concatenates adjacent cells. Replacing each table with a
pipe-delimited text form first keeps cell values as distinct tokens, which
is what makes a quote like "4.50%" recoverable from page text.
"""

from __future__ import annotations

from bs4 import BeautifulSoup, Tag


def linearize_tables(soup: BeautifulSoup) -> None:
    """Replace every <table> in-place with pipe-delimited row text."""
    for table in soup.find_all("table"):
        if not isinstance(table, Tag):
            continue
        rows: list[str] = []
        for tr in table.find_all("tr"):
            if not isinstance(tr, Tag):
                continue
            cells = [
                cell.get_text(" ", strip=True)
                for cell in tr.find_all(["th", "td"])
                if isinstance(cell, Tag)
            ]
            if cells:
                rows.append(" | ".join(cells))
        replacement = "\n".join(rows)
        table.replace_with(replacement)
