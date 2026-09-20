from evals.scorecard import ExtractedField, required_recall, score_document
from fundspine.ingest.loader import Page


def test_scorecard_exact_match_and_citation() -> None:
    pages = (
        Page(
            page_no=1,
            text="Net return for the quarter was 3.55%. Gross return for the quarter was 4.50%.",
        ),
    )
    truth = [
        {
            "field_path": "metrics.net_return_bps",
            "value_numeric": 355,
            "value_text": None,
            "period": "2026Q1",
            "page_no": 1,
            "quote": "Net return for the quarter was 3.55%.",
        },
        {
            "field_path": "metrics.gross_return_bps",
            "value_numeric": 450,
            "value_text": None,
            "period": "2026Q1",
            "page_no": 1,
            "quote": "Gross return for the quarter was 4.50%.",
        },
    ]
    extracted = [
        ExtractedField(
            field_path="metrics.net_return_bps",
            period="2026Q1",
            value_numeric=355,
            value_text=None,
            page_no=1,
            quote="Net return for the quarter was 3.55%.",
        ),
        ExtractedField(
            field_path="metrics.gross_return_bps",
            period="2026Q1",
            value_numeric=449,
            value_text=None,
            page_no=1,
            quote="Gross return for the quarter was 4.50%.",
        ),
    ]
    score = score_document(stem="doc_1", truth_facts=truth, extracted=extracted, pages=pages)
    assert score.citation_valid == 1.0
    assert score.recall["metrics.net_return_bps@2026Q1"] is True
    assert score.exact["metrics.net_return_bps@2026Q1"] is True
    assert score.exact["metrics.gross_return_bps@2026Q1"] is False
    assert required_recall(score) == 1.0
