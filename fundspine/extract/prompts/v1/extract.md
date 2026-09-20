# Extract cited facts from a fund document.

You receive page text from one document about one fund. Return every field
you can support with a verbatim quote.

## Hard rules

1. `quote` must be an exact substring of the cited page's text. Copy characters
   verbatim. If you cannot find a verbatim quote, omit the field.
2. `value_as_written` is the figure or phrase **as it appears** in the document.
   Do not convert percentages to basis points, do not strip currency symbols,
   do not round. Conversion is someone else's job.
3. Emit no field_path that is not in the closed list below.
4. Do not invent numbers. If a field is missing from the document, omit it.
5. `period` is `YYYYQN` (for example `2026Q1`) when the value belongs to a
   reporting quarter. Terms that are standing economics may use null.
6. A restated prior-period figure is a separate fact: same field_path, the
   **prior** period, and a quote that names the restatement.

## Closed field_path list

- fund.name
- fund.manager_name
- fund.strategy_family
- fund.share_class
- metrics.gross_return_bps
- metrics.net_return_bps
- metrics.ytd_return_bps
- metrics.nav_usd_cents
- metrics.sharpe_36m
- metrics.max_drawdown_bps
- terms.mgmt_fee_bps
- terms.perf_fee_bps
- terms.hurdle_bps
- terms.lockup_months
- terms.notice_days
- narrative.strategy

## value_as_written examples

- returns and fees: `4.50%`, `1.50%`, `20%`, `-11.50%`
- NAV: `$128,430,000.00`
- Sharpe: `1.42`
- lockup / notice: `12`, `90`
- names and narrative: the full string as written
