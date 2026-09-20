"""HTML → pages. The PDF adapter, when it exists, returns the same shape."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from fundspine.ingest.tables import linearize_tables

_WHITESPACE = re.compile(r"[ \t\u00a0]+")


@dataclass(frozen=True)
class Page:
    page_no: int
    text: str


@dataclass(frozen=True)
class ParsedDocument:
    source_uri: str
    sha256: str
    html: str
    pages: tuple[Page, ...]

    @property
    def page_count(self) -> int:
        return len(self.pages)

    def text_for(self, page_no: int) -> str:
        for page in self.pages:
            if page.page_no == page_no:
                return page.text
        raise ValueError(f"no page {page_no} in {self.source_uri}")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_text(text: str) -> str:
    """Collapse horizontal whitespace; drop empty lines. Quotes are matched
    against this form, so the golden generator uses the same function."""
    lines = [_WHITESPACE.sub(" ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def pages_from_html(html: str) -> tuple[Page, ...]:
    soup = BeautifulSoup(html, "html.parser")
    linearize_tables(soup)
    sections = soup.select("section.page")
    if not sections:
        raise ValueError("document has no <section class='page'> divisions")

    pages: list[Page] = []
    for section in sections:
        if not isinstance(section, Tag):
            continue
        raw_no = section.get("data-page-no")
        if not isinstance(raw_no, str):
            raise ValueError("page section is missing data-page-no")
        page_no = int(raw_no)
        text = normalize_text(section.get_text("\n", strip=True))
        if not text:
            raise ValueError(f"page {page_no} has no text after tag stripping")
        pages.append(Page(page_no=page_no, text=text))

    expected = list(range(1, len(pages) + 1))
    got = [p.page_no for p in pages]
    if got != expected:
        raise ValueError(f"page numbers must be contiguous from 1; got {got}")
    return tuple(pages)


def parse_html(html: str, *, source_uri: str, sha256: str | None = None) -> ParsedDocument:
    encoded = html.encode("utf-8")
    return ParsedDocument(
        source_uri=source_uri,
        sha256=sha256 if sha256 is not None else sha256_hex(encoded),
        html=html,
        pages=pages_from_html(html),
    )


def load_html_file(path: Path) -> ParsedDocument:
    data = path.read_bytes()
    html = data.decode("utf-8")
    return parse_html(html, source_uri=path.resolve().as_uri(), sha256=sha256_hex(data))
