"""Tests for predictive analysis engine (offline)."""
from smf_swarm.analysis import (
    Attachment,
    PredictiveSwarmEngine,
    extract_text_from_bytes,
)


def test_csv_extract_summary():
    raw = b"name,value\nalpha,10\nbeta,20\ngamma,30\n"
    text = extract_text_from_bytes("sample.csv", raw, "text/csv")
    assert "CSV columns" in text
    assert "value" in text
    assert "mean=" in text


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
    assert 0 < report.confidence <= 1
    assert report.chain_valid
    assert report.persona_views
    assert "pipeline.csv" in report.attachments_used
    d = report.to_dict()
    assert d["mode"] == "mock"
    assert d["key_drivers"]


def test_question_required():
    engine = PredictiveSwarmEngine(mode="mock")
    try:
        engine.run("   ")
        assert False, "expected ValueError"
    except ValueError:
        pass
