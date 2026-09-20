from pathlib import Path

from evals.golden import numbers as N
from evals.golden.generate import generate_all
from fundspine.ingest.loader import load_html_file


def test_generate_writes_three_docs_and_derived_truth(tmp_path: Path) -> None:
    dest = generate_all(tmp_path)
    for stem in ("doc_1", "doc_2", "doc_3"):
        assert (dest / f"{stem}.html").exists()
        assert (dest / f"{stem}.truth.json").exists()
    assert (dest / "fund.json").exists()


def test_every_truth_quote_is_a_verbatim_substring(tmp_path: Path) -> None:
    import json

    dest = generate_all(tmp_path)
    for stem in ("doc_1", "doc_2", "doc_3"):
        parsed = load_html_file(dest / f"{stem}.html")
        truth = json.loads((dest / f"{stem}.truth.json").read_text())
        assert parsed.pages
        for fact in truth["facts"]:
            assert fact["quote"] in parsed.text_for(fact["page_no"]), fact["field_path"]


def test_doc1_fee_bridge_closes() -> None:
    q_mgmt = round(N.MGMT_FEE_BPS / 4)
    q_hurdle = round(N.HURDLE_BPS / 4)
    excess = max(0, N.Q1_GROSS_BPS - q_hurdle)
    q_perf = round((N.PERF_FEE_BPS / 10000.0) * excess)
    assert N.Q1_GROSS_BPS - q_mgmt - q_perf == N.Q1_NET_BPS


def test_doc2_is_forty_bps_off_the_bridge() -> None:
    assert N.DOC2_NET_BPS - N.Q1_NET_BPS == 40


def test_doc3_restates_nav_and_reprices_the_fee(tmp_path: Path) -> None:
    import json

    dest = generate_all(tmp_path)
    truth = json.loads((dest / "doc_3.truth.json").read_text())
    navs = [
        f
        for f in truth["facts"]
        if f["field_path"] == "metrics.nav_usd_cents"
    ]
    periods = {f["period"]: f["value_numeric"] for f in navs}
    assert periods[N.Q1] == N.Q1_NAV_RESTATED_USD_CENTS
    assert periods[N.Q2] == N.Q2_NAV_USD_CENTS
    mgmt = next(f for f in truth["facts"] if f["field_path"] == "terms.mgmt_fee_bps")
    assert mgmt["value_numeric"] == N.Q2_MGMT_FEE_BPS
    assert "1 April 2026" in mgmt["quote"]
