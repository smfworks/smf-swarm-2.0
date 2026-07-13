"""Tests for charts, share, and series extraction (v0.4)."""
from smf_swarm.analysis.series import (
    extract_series_from_csv,
    sparkline_svg,
)
from smf_swarm.app.auth import new_share_id, sign_run_id, verify_run_signature
from smf_swarm.analysis import Attachment, PredictiveSwarmEngine
from smf_swarm.analysis.series import extract_series_from_attachment_bytes


def test_sparkline_svg_nonempty():
    svg = sparkline_svg([1, 3, 2, 5, 4])
    assert svg.startswith("<svg")
    assert "polyline" in svg


def test_extract_csv_series():
    csv = "week,signups,churn\n1,10,1\n2,12,2\n3,15,1\n4,14,3\n"
    series = extract_series_from_csv("growth.csv", csv)
    assert series
    assert series[0].sparkline_svg
    assert series[0].stats["n"] >= 3


def test_engine_includes_charts():
    raw = b"week,signups\n1,10\n2,14\n3,18\n4,20\n"
    charts = extract_series_from_attachment_bytes("g.csv", raw, "text/csv")
    att = Attachment(
        filename="g.csv",
        content_type="text/csv",
        text="CSV summary",
        size_bytes=len(raw),
        charts=charts,
    )
    report = PredictiveSwarmEngine(mode="mock").run("Will signups rise?", [att])
    assert report.charts
    assert report.charts[0]["sparkline_svg"]


def test_share_signature():
    rid = "abc123"
    sig = sign_run_id(rid)
    assert verify_run_signature(rid, sig)
    assert not verify_run_signature(rid, "deadbeef")
    assert new_share_id()
