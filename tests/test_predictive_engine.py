"""Tests for predictive analysis engine (offline) v0.3."""
from smf_swarm.analysis import (
    Attachment,
    PredictiveSwarmEngine,
    extract_text_from_bytes,
    normalize_scenarios,
)
from smf_swarm.app.history import RunHistory


def test_csv_extract_summary():
    raw = b"name,value\nalpha,10\nbeta,20\ngamma,30\n"
    text = extract_text_from_bytes("sample.csv", raw, "text/csv")
    assert "CSV columns" in text
    assert "mean=" in text


def test_normalize_scenarios_percent():
    s = normalize_scenarios(
        [{"name": "Base", "probability": 0.6, "narrative": "x"}]
    )
    assert s[0]["probability"] == "60%"


def test_mock_predictive_with_attachment():
    engine = PredictiveSwarmEngine(mode="mock")
    att = Attachment(
        filename="pipeline.csv",
        content_type="text/csv",
        text=extract_text_from_bytes(
            "pipeline.csv",
            b"stage,count\nlead,100\nqualified,40\nwon,12\n",
            "text/csv",
        ),
        size_bytes=40,
    )
    report = engine.run(
        "What is the likely conversion outlook and main risks for this funnel?",
        [att],
    )
    assert report.prediction
    assert report.prediction_headline
    assert report.prediction_detail
    assert 0 < report.confidence <= 1
    assert report.chain_valid
    assert report.persona_views
    assert report.evidence
    assert report.methodology.get("personas")
    assert "pipeline.csv" in report.attachments_used
    md = report.to_markdown()
    assert "Prediction" in md and report.run_id in md
    d = report.to_dict()
    assert d["mode"] == "mock"
    assert d["evidence"]


def test_question_required():
    engine = PredictiveSwarmEngine(mode="mock")
    try:
        engine.run("   ")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_history_roundtrip(tmp_path):
    h = RunHistory(path=tmp_path / "h.jsonl", max_entries=10)
    engine = PredictiveSwarmEngine(mode="mock")
    report = engine.run("Will growth continue?", [])
    h.append(report.to_dict())
    items = h.list()
    assert items
    assert items[0]["run_id"] == report.run_id
    got = h.get(report.run_id)
    assert got and got["question"] == "Will growth continue?"
