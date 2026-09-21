"""Unit economics. Money is integer USD micros. There is no float dollar."""

from __future__ import annotations

from collections.abc import Sequence

# gpt-4o-2024-08-06 list price (OpenAI, Sep 2026): $2.50 / 1M in, $10.00 / 1M out.
INPUT_USD_MICROS_PER_MILLION = 2_500_000
OUTPUT_USD_MICROS_PER_MILLION = 10_000_000
MODEL = "gpt-4o-2024-08-06"

# Stated assumptions for the whole-book extrapolation. Correct them and redo.
FUNDS_ON_PLATFORM = 40
DOCS_PER_FUND_PER_YEAR = 4
PARTNERS_RECEIVING_COMMENTARY = 7


def cost_micros(tokens_in: int, tokens_out: int) -> int:
    if tokens_in < 0 or tokens_out < 0:
        raise ValueError("token counts must be non-negative")
    return (
        tokens_in * INPUT_USD_MICROS_PER_MILLION + tokens_out * OUTPUT_USD_MICROS_PER_MILLION
    ) // 1_000_000


def format_usd(micros: int) -> str:
    sign = "-" if micros < 0 else ""
    dollars, rem = divmod(abs(micros), 1_000_000)
    return f"{sign}${dollars}.{rem:06d}"


def mean_micros(values: Sequence[int]) -> int:
    if not values:
        raise RuntimeError("cannot average an empty cost series")
    return sum(values) // len(values)


def render_costs_table(
    *,
    rows: Sequence[tuple[str, int, int, int]],
    mean_document_micros: int,
) -> str:
    """rows: (label, tokens_in, tokens_out, micros)."""
    lines = [
        f"model: {MODEL}",
        "rate: $2.50 / 1M input tokens, $10.00 / 1M output tokens",
        "prose: not billed (tone-enum templates, not an LLM)",
        "",
        "| document | tokens_in | tokens_out | cost |",
        "|---|---|---|---|",
    ]
    for label, tokens_in, tokens_out, micros in rows:
        lines.append(
            f"| {label} | {tokens_in} | {tokens_out} | {format_usd(micros)} |"
        )
    lines.extend(
        [
            "",
            f"rate per document (mean of {len(rows)}): {format_usd(mean_document_micros)}",
            (
                "rate per partner packet: "
                f"{format_usd(mean_document_micros)} "
                "(one extract; render is $0; packet is not re-extracted per partner)"
            ),
            "",
            "assumptions (stated so they can be corrected):",
            f"  funds on platform: {FUNDS_ON_PLATFORM}",
            f"  documents per fund per year: {DOCS_PER_FUND_PER_YEAR}",
            f"  partners receiving commentary: {PARTNERS_RECEIVING_COMMENTARY}",
            "  extracts per fund per quarter: 1",
            "",
            "| horizon | extracts | model spend |",
            "|---|---|---|",
        ]
    )
    quarterly_extracts = FUNDS_ON_PLATFORM
    yearly_extracts = FUNDS_ON_PLATFORM * DOCS_PER_FUND_PER_YEAR
    quarterly = mean_document_micros * quarterly_extracts
    yearly = mean_document_micros * yearly_extracts
    packets_per_quarter = FUNDS_ON_PLATFORM * PARTNERS_RECEIVING_COMMENTARY
    lines.append(
        f"| one quarter | {quarterly_extracts} | {format_usd(quarterly)} |"
    )
    lines.append(
        f"| one year | {yearly_extracts} | {format_usd(yearly)} |"
    )
    lines.append(
        "| partner packets / quarter (not extra LLM) | "
        f"{packets_per_quarter} | {format_usd(quarterly)} |"
    )
    lines.append("")
    lines.append(
        "These goldens are short HTML tearsheets. A real manager PDF with scans "
        "would raise tokens_in; the multiplication is the same."
    )
    return "\n".join(lines) + "\n"
