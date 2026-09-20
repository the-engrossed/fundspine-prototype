"""The three synthetic documents. These numbers ARE the documents.

Aligned to the hand-written R001_fee_bridge:
  q_mgmt   = round(mgmt_fee_bps / 4)
  q_hurdle = round(hurdle_bps / 4)
  excess   = max(0, gross - q_hurdle)
  q_perf   = round((perf_fee_bps / 10000.0) * excess)
  expected_net = gross - q_mgmt - q_perf
"""

from __future__ import annotations

from datetime import date

FUND_ID = "7c8e2a10-6b3d-4d2a-9f1e-0c4b7a9d1234"
FUND_NAME = "Meridian Systematic Macro Fund"
MANAGER_NAME = "Meridian Capital Management"
STRATEGY_FAMILY = "Systematic Global Macro"
SHARE_CLASS = "Class A"
CURRENCY = "USD"
INCEPTION = date(2018, 3, 1)
FIRM_AUM_USD_CENTS = 48_000_000_000  # $480,000,000.00

MGMT_FEE_BPS = 150
PERF_FEE_BPS = 2_000
HURDLE_BPS = 500
LOCKUP_MONTHS = 12
NOTICE_DAYS = 90

# Q1 2026 — internally consistent with R001 (expected net 347 bps).
Q1 = "2026Q1"
Q1_JAN_BPS = 140
Q1_FEB_BPS = 90
Q1_MAR_BPS = 220
Q1_GROSS_BPS = 450
Q1_NET_BPS = 347
Q1_YTD_BPS = 347
Q1_NAV_USD_CENTS = 12_843_000_000  # $128,430,000.00
Q1_SHARPE_36M = 14_200  # 1.42x
Q1_MAX_DRAWDOWN_BPS = -1_150  # -11.50%
DOC2_NET_BPS = 387  # 40 bps too high; R001 must fire

# Q2 2026 — restated Q1 NAV + 175 bps fee from 1 April 2026.
Q2 = "2026Q2"
Q2_MGMT_FEE_BPS = 175
Q2_APR_BPS = 80
Q2_MAY_BPS = -30
Q2_JUN_BPS = 170
Q2_GROSS_BPS = 220
Q2_NET_BPS = 157
Q2_YTD_BPS = 504
Q1_NAV_RESTATED_USD_CENTS = 12_791_000_000  # $127,910,000.00
Q2_NAV_USD_CENTS = 13_015_000_000  # $130,150,000.00
Q2_SHARPE_36M = 13_800  # 1.38x
Q2_MAX_DRAWDOWN_BPS = -1_210  # -12.10%
FEE_EFFECTIVE = date(2026, 4, 1)

STRATEGY_NARRATIVE = (
    "Meridian Systematic Macro Fund implements a systematic global macro programme "
    "spanning rates, currencies, equity indices and commodities. Signals combine "
    "trend-following, carry and relative-value features, sized by inverse volatility "
    "and capped by a portfolio risk budget. The book is expressed exclusively through "
    "exchange-traded futures; there is no cash equity, no OTC derivative and no "
    "private credit sleeve. Diversification comes from forty liquid futures markets "
    "rather than from a large number of correlated equity names. Positions are "
    "initiated and retired by rule, not by a discretionary overlay, and the same "
    "rule set applies in every region. The objective is a return stream with low "
    "correlation to traditional balanced portfolios and a drawdown profile that is "
    "acceptable to family offices and wealth platforms. Liquidity is daily at the "
    "instrument level; investor liquidity is governed by the lockup and notice "
    "provisions in the terms. The research group at Meridian Capital Management "
    "continues to harvest new markets only when a contract clears the programme's "
    "liquidity and cost filters. Capacity is managed conservatively relative to "
    "firm assets so that market impact does not become the binding constraint."
)
