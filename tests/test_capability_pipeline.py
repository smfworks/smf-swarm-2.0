"""Tests for capability diagnostic + phase1 pipeline."""
from smf_swarm.capability import CapabilityDiagnostic, MockCapabilityBackend
from smf_swarm.pipeline import CAPABILITY_DIAGNOSE, Phase1Pipeline
from smf_swarm.governance import PermissionDenied
import pytest


def test_mock_diagnostic_returns_ranked_gaps():
    diag = CapabilityDiagnostic(backend=MockCapabilityBackend())
    gaps = diag.diagnose(
        successful_trajectories=[{"content": "Selected 2 hypotheses. Clear risks."}],
        failed_trajectories=[
            {"content": "Selected too many hypotheses. No risk analysis."},
            {"content": "Vague non-executable plan."},
        ],
        domain="article_editing",
    )
    assert gaps
    assert gaps[0].failure_coverage >= gaps[-1].failure_coverage
    assert gaps[0].name
    assert gaps[0].suggested_criterion


def test_phase1_pipeline_happy_path(tmp_path):
    pipe = Phase1Pipeline(audit_path=tmp_path / "a.jsonl")
    aid = pipe.bootstrap_agent("Diagnostic Agent", agent_id="diag1")
    result = pipe.run_diagnosis(
        aid,
        successful=[{"content": "Good triage, 2 hypotheses, risks listed."}],
        failed=[{"content": "Too many hypotheses, vague, no risk."}],
        domain="article_editing",
    )
    assert result.gaps
    assert result.chain_valid
    assert result.audit_events >= 3


def test_phase1_denies_without_grant():
    pipe = Phase1Pipeline()
    reg = pipe.identities.register("Rogue", agent_id="rogue")
    # no grant
    with pytest.raises(PermissionDenied):
        pipe.run_diagnosis(
            reg.agent_id,
            successful=[{"content": "ok"}],
            failed=[{"content": "fail"}],
        )
