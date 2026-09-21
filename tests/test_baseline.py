import json
from pathlib import Path

from evals.scorecard import regression_messages

BASELINE = Path(__file__).resolve().parents[1] / "evals" / "scorecards" / "baseline.json"
V1 = Path(__file__).resolve().parents[1] / "evals" / "scorecards" / "v1_before.json"


def test_baseline_meets_approved_floors() -> None:
    data = json.loads(BASELINE.read_text(encoding="utf-8"))
    assert data["prompt_version"] == "v2"
    by_stem = {doc["stem"]: doc for doc in data["documents"]}
    assert by_stem["doc_1"]["citation_validity"] == 1.0
    assert by_stem["doc_2"]["citation_validity"] == 1.0
    assert by_stem["doc_3"]["citation_validity"] == 1.0
    assert by_stem["doc_1"]["required_recall"] == 1.0
    assert by_stem["doc_2"]["required_recall"] == 1.0
    assert by_stem["doc_3"]["required_recall"] >= 0.90
    assert by_stem["doc_1"]["exact_matches"] == 16
    assert by_stem["doc_2"]["exact_matches"] == 16
    assert regression_messages(data, data) == []


def test_v2_baseline_improves_required_recall_over_v1() -> None:
    v1 = json.loads(V1.read_text(encoding="utf-8"))
    v2 = json.loads(BASELINE.read_text(encoding="utf-8"))
    v1_by = {doc["stem"]: doc for doc in v1["documents"]}
    v2_by = {doc["stem"]: doc for doc in v2["documents"]}
    for stem in ("doc_1", "doc_2", "doc_3"):
        assert v2_by[stem]["required_recall"] >= v1_by[stem]["required_recall"]
        assert v2_by[stem]["citation_validity"] >= v1_by[stem]["citation_validity"]


def test_regression_messages_catch_an_exact_match_drop() -> None:
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    worse = json.loads(json.dumps(baseline))
    worse["documents"][0]["exact_matches"] = 0
    messages = regression_messages(worse, baseline)
    assert any("exact_matches" in item for item in messages)
