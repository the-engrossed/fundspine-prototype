from __future__ import annotations

from evals.golden import numbers as N
from evals.golden.format import (
    TruthFact,
    TruthRecorder,
    fmt_bps_rate,
    fmt_pct,
    fmt_ratio,
    fmt_usd,
)
from evals.golden.html import wrap


def build_doc1() -> tuple[str, list[TruthFact], dict[str, str]]:
    t = TruthRecorder()
    p1, p2, p3 = 1, 2, 3
    fund = t.text("fund.name", N.FUND_NAME, p1, N.FUND_NAME)
    manager = t.text("fund.manager_name", N.MANAGER_NAME, p1, N.MANAGER_NAME)
    strategy = t.text("fund.strategy_family", N.STRATEGY_FAMILY, p1, N.STRATEGY_FAMILY)
    share = t.text("fund.share_class", N.SHARE_CLASS, p1, N.SHARE_CLASS)

    jan, feb, mar = fmt_pct(N.Q1_JAN_BPS), fmt_pct(N.Q1_FEB_BPS), fmt_pct(N.Q1_MAR_BPS)
    gross_s, net_s, ytd_s = fmt_pct(N.Q1_GROSS_BPS), fmt_pct(N.Q1_NET_BPS), fmt_pct(N.Q1_YTD_BPS)
    nav_s, sharpe_s, dd_s = fmt_usd(N.Q1_NAV_USD_CENTS), fmt_ratio(N.Q1_SHARPE_36M), fmt_pct(
        N.Q1_MAX_DRAWDOWN_BPS
    )
    gross_q = f"Gross return for the quarter was {gross_s}."
    net_q = f"Net return for the quarter was {net_s}."
    ytd_q = f"Year-to-date net return was {ytd_s}."
    nav_q = f"Net asset value at 31 March 2026 was {nav_s}."
    sharpe_q = f"The thirty-six month Sharpe ratio was {sharpe_s}."
    dd_q = f"Maximum drawdown over the same window was {dd_s}."
    t.numeric("metrics.gross_return_bps", N.Q1_GROSS_BPS, "bps", p1, gross_q, N.Q1)
    t.numeric("metrics.net_return_bps", N.Q1_NET_BPS, "bps", p1, net_q, N.Q1)
    t.numeric("metrics.ytd_return_bps", N.Q1_YTD_BPS, "bps", p1, ytd_q, N.Q1)
    t.numeric("metrics.nav_usd_cents", N.Q1_NAV_USD_CENTS, "usd_cents", p1, nav_q, N.Q1)
    t.numeric("metrics.sharpe_36m", N.Q1_SHARPE_36M, "ratio_bps", p2, sharpe_q, N.Q1)
    t.numeric("metrics.max_drawdown_bps", N.Q1_MAX_DRAWDOWN_BPS, "bps", p2, dd_q, N.Q1)

    mgmt_s, perf_s, hurdle_s = fmt_bps_rate(N.MGMT_FEE_BPS), fmt_pct(N.PERF_FEE_BPS), fmt_bps_rate(
        N.HURDLE_BPS
    )
    lock_s, notice_s = str(N.LOCKUP_MONTHS), str(N.NOTICE_DAYS)
    mgmt_q = f"Management fee {mgmt_s} per annum."
    perf_q = f"Performance fee {perf_s} of profits."
    hurdle_q = f"Hurdle rate {hurdle_s} per annum."
    lock_q = f"Lockup period {lock_s} months."
    notice_q = f"Redemption notice {notice_s} days."
    t.numeric("terms.mgmt_fee_bps", N.MGMT_FEE_BPS, "bps", p2, mgmt_q, None)
    t.numeric("terms.perf_fee_bps", N.PERF_FEE_BPS, "bps", p2, perf_q, None)
    t.numeric("terms.hurdle_bps", N.HURDLE_BPS, "bps", p2, hurdle_q, None)
    t.numeric("terms.lockup_months", N.LOCKUP_MONTHS, "months", p2, lock_q, None)
    t.numeric("terms.notice_days", N.NOTICE_DAYS, "days", p2, notice_q, None)
    narrative = t.text(
        "narrative.strategy",
        N.STRATEGY_NARRATIVE,
        p3,
        "Diversification comes from forty liquid futures markets",
    )
    body = f"""
<section class="page" data-page-no="1">
  <p class="kicker">{manager} · {share}</p>
  <h1>{fund}</h1>
  <p class="meta">{strategy} · Tearsheet · {N.Q1} · Published 12 April 2026</p>
  <h2>Performance</h2>
  <table>
    <tr><th>Month</th><th class="num">Return</th></tr>
    <tr><td>January 2026</td><td class="num">{jan}</td></tr>
    <tr><td>February 2026</td><td class="num">{feb}</td></tr>
    <tr><td>March 2026</td><td class="num">{mar}</td></tr>
    <tr><td>Gross, first quarter</td><td class="num">{gross_s}</td></tr>
    <tr><td>Net, first quarter</td><td class="num">{net_s}</td></tr>
    <tr><td>Year-to-date net</td><td class="num">{ytd_s}</td></tr>
  </table>
  <p>{gross_q} {net_q} {ytd_q} {nav_q}</p>
</section>
<section class="page" data-page-no="2">
  <h1>{fund}</h1>
  <p class="meta">Terms in force · Class A · as of 31 March 2026</p>
  <h2>Terms</h2>
  <table>
    <tr><th>Item</th><th class="num">Term</th></tr>
    <tr><td>Management fee</td><td class="num">{mgmt_s} per annum</td></tr>
    <tr><td>Performance fee</td><td class="num">{perf_s} of profits</td></tr>
    <tr><td>Hurdle</td><td class="num">{hurdle_s} per annum</td></tr>
    <tr><td>High water mark</td><td class="num">Yes</td></tr>
    <tr><td>Lockup</td><td class="num">{lock_s} months</td></tr>
    <tr><td>Redemption notice</td><td class="num">{notice_s} days</td></tr>
  </table>
  <p>{mgmt_q} {perf_q} {hurdle_q} High water mark applies. {lock_q} {notice_q}</p>
  <h2>Risk</h2>
  <p>{sharpe_q} {dd_q}</p>
</section>
<section class="page" data-page-no="3">
  <h1>{fund}</h1>
  <h2>Strategy</h2>
  <p>{narrative}</p>
</section>
"""
    meta = {"stem": "doc_1", "doc_type": "tearsheet", "period": N.Q1, "published_on": "2026-04-12"}
    return wrap(f"{fund} · {N.Q1} Tearsheet", body), t.facts, meta


def build_doc2() -> tuple[str, list[TruthFact], dict[str, str]]:
    t = TruthRecorder()
    p1, p2 = 1, 2
    fund = t.text("fund.name", N.FUND_NAME, p1, N.FUND_NAME)
    manager = t.text("fund.manager_name", N.MANAGER_NAME, p1, N.MANAGER_NAME)
    strategy = t.text("fund.strategy_family", N.STRATEGY_FAMILY, p1, N.STRATEGY_FAMILY)
    share = t.text("fund.share_class", N.SHARE_CLASS, p1, N.SHARE_CLASS)
    gross_s = fmt_pct(N.Q1_GROSS_BPS)
    net_s = fmt_pct(N.DOC2_NET_BPS)
    ytd_s = fmt_pct(N.DOC2_NET_BPS)
    nav_s, sharpe_s, dd_s = fmt_usd(N.Q1_NAV_USD_CENTS), fmt_ratio(N.Q1_SHARPE_36M), fmt_pct(
        N.Q1_MAX_DRAWDOWN_BPS
    )
    mgmt_s, perf_s, hurdle_s = fmt_bps_rate(N.MGMT_FEE_BPS), fmt_pct(N.PERF_FEE_BPS), fmt_bps_rate(
        N.HURDLE_BPS
    )
    gross_q = f"Gross return for the quarter was {gross_s}."
    net_q = f"Net return for the quarter was {net_s}."
    ytd_q = f"Year-to-date net return was {ytd_s}."
    nav_q = f"Net asset value at 31 March 2026 was {nav_s}."
    sharpe_q = f"The thirty-six month Sharpe ratio was {sharpe_s}."
    dd_q = f"Maximum drawdown over the same window was {dd_s}."
    mgmt_q = f"Management fee {mgmt_s} per annum."
    perf_q = f"Performance fee {perf_s} of profits."
    hurdle_q = f"Hurdle rate {hurdle_s} per annum."
    lock_q = f"Lockup period {N.LOCKUP_MONTHS} months."
    notice_q = f"Redemption notice {N.NOTICE_DAYS} days."
    t.numeric("metrics.gross_return_bps", N.Q1_GROSS_BPS, "bps", p1, gross_q, N.Q1)
    t.numeric("metrics.net_return_bps", N.DOC2_NET_BPS, "bps", p1, net_q, N.Q1)
    t.numeric("metrics.ytd_return_bps", N.DOC2_NET_BPS, "bps", p1, ytd_q, N.Q1)
    t.numeric("metrics.nav_usd_cents", N.Q1_NAV_USD_CENTS, "usd_cents", p1, nav_q, N.Q1)
    t.numeric("metrics.sharpe_36m", N.Q1_SHARPE_36M, "ratio_bps", p2, sharpe_q, N.Q1)
    t.numeric("metrics.max_drawdown_bps", N.Q1_MAX_DRAWDOWN_BPS, "bps", p2, dd_q, N.Q1)
    t.numeric("terms.mgmt_fee_bps", N.MGMT_FEE_BPS, "bps", p2, mgmt_q, None)
    t.numeric("terms.perf_fee_bps", N.PERF_FEE_BPS, "bps", p2, perf_q, None)
    t.numeric("terms.hurdle_bps", N.HURDLE_BPS, "bps", p2, hurdle_q, None)
    t.numeric("terms.lockup_months", N.LOCKUP_MONTHS, "months", p2, lock_q, None)
    t.numeric("terms.notice_days", N.NOTICE_DAYS, "days", p2, notice_q, None)
    t.text(
        "narrative.strategy",
        N.STRATEGY_NARRATIVE,
        p2,
        "Positions are initiated and retired by rule, not by a discretionary overlay",
    )
    body = f"""
<section class="page" data-page-no="1">
  <p class="kicker">{manager} · Monthly letter</p>
  <h1>{fund}</h1>
  <p class="meta">{strategy} · {share} · {N.Q1} · Published 18 April 2026</p>
  <h2>Letter to investors</h2>
  <p>Markets rewarded patience in rates and metals. {gross_q} {net_q} {ytd_q}</p>
  <p>{nav_q} Firm assets remain {fmt_usd(N.FIRM_AUM_USD_CENTS)}.</p>
</section>
<section class="page" data-page-no="2">
  <h2>Terms and risk</h2>
  <p>{mgmt_q} {perf_q} {hurdle_q} High water mark applies. {lock_q} {notice_q}</p>
  <p>{sharpe_q} {dd_q}</p>
  <h2>Strategy</h2>
  <p>{N.STRATEGY_NARRATIVE}</p>
</section>
"""
    meta = {
        "stem": "doc_2",
        "doc_type": "monthly_letter",
        "period": N.Q1,
        "published_on": "2026-04-18",
    }
    return wrap(f"{fund} · {N.Q1} Letter", body), t.facts, meta
