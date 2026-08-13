"""Production-hardening tests: config, CLI, audit, share secret, engine defaults."""
from __future__ import annotations

import inspect

import pytest

from smf_swarm.analysis import PredictiveSwarmEngine
from smf_swarm.app.auth import share_secret, sign_run_id, verify_run_signature
from smf_swarm.cli import main as cli_main
from smf_swarm.config import (
    normalize_llm_base_url,
    optional_model_id,
    safe_filename,
    validate_model_id,
)
from smf_swarm.governance import AuditLog


def test_normalize_rejects_credentials_and_metadata():
    with pytest.raises(ValueError, match="credentials"):
        normalize_llm_base_url("http://user:pass@127.0.0.1:8888/v1")
    with pytest.raises(ValueError, match="metadata"):
        normalize_llm_base_url("http://169.254.169.254/latest/meta-data")
    with pytest.raises(ValueError, match="metadata"):
        normalize_llm_base_url("http://metadata.google.internal/computeMetadata/v1/")
    with pytest.raises(ValueError, match="absolute HTTP"):
        normalize_llm_base_url("ftp://example.com/v1")


def test_normalize_accepts_local_openai_compatible():
    assert (
        normalize_llm_base_url("http://127.0.0.1:8888/v1")
        == "http://127.0.0.1:8888/v1"
    )


def test_model_id_validation():
    assert validate_model_id("  my-model  ") == "my-model"
    with pytest.raises(ValueError, match="required"):
        validate_model_id("   ")
    with pytest.raises(ValueError, match="control"):
        validate_model_id("bad\nmodel")
    assert optional_model_id("") is None
    assert optional_model_id(None) is None


def test_safe_filename_strips_path():
    assert safe_filename("../../etc/passwd") == "passwd"
    assert safe_filename("") == "upload"
    assert safe_filename(".") == "upload"


def test_engine_llm_requires_explicit_endpoint(monkeypatch):
    monkeypatch.delenv("SMF_SWARM_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("SMF_SWARM_LLM_MODEL", raising=False)
    with pytest.raises(ValueError, match="LLM mode requires llm_base_url"):
        PredictiveSwarmEngine(mode="llm")


def test_engine_has_no_lab_host_default():
    src = inspect.getsource(PredictiveSwarmEngine.__init__)
    assert "spark-56bc" not in src
    assert "not-needed" not in src
    assert "unsloth/" not in src


def test_share_secret_is_not_hardcoded(monkeypatch):
    monkeypatch.delenv("SMF_SWARM_SHARE_SECRET", raising=False)
    monkeypatch.delenv("SMF_SWARM_API_TOKEN", raising=False)
    import smf_swarm.app.auth as auth

    auth._ephemeral_share_secret = None
    secret = share_secret()
    assert secret
    assert secret != "smf-swarm-dev-share-secret"
    assert share_secret() == secret
    rid = "abc123"
    assert verify_run_signature(rid, sign_run_id(rid))


def test_audit_skips_corrupt_lines(tmp_path):
    path = tmp_path / "audit.jsonl"
    good = AuditLog(path=path)
    good.append(agent_id="a", action="ok", resource="r", outcome="success")
    path.write_text(path.read_text(encoding="utf-8") + "{not-json}\n", encoding="utf-8")
    reloaded = AuditLog(path=path)
    assert len(reloaded) == 1
    assert reloaded.verify_chain()


def test_cli_missing_question_exits_2():
    assert cli_main(["analyze"]) == 2


def test_cli_missing_data_file_exits_2(tmp_path):
    missing = tmp_path / "nope.csv"
    assert cli_main(["analyze", "-q", "Outlook?", "-d", str(missing)]) == 2


def test_cli_mock_analyze_ok(tmp_path):
    data = tmp_path / "s.csv"
    data.write_text("week,n\n1,10\n2,12\n3,14\n", encoding="utf-8")
    out = tmp_path / "report.json"
    assert cli_main(["analyze", "-q", "Will it grow?", "-d", str(data), "-o", str(out)]) == 0
    assert out.is_file()
