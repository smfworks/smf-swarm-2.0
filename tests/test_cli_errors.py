"""CLI error paths."""
from __future__ import annotations

from smf_swarm.app.auth import is_loopback_bind, require_share_secret_for_bind
from smf_swarm.cli import main
import pytest


def test_analyze_missing_data_file_exits_2(tmp_path) -> None:
    missing = tmp_path / "no-such.csv"
    code = main(["analyze", "-q", "Smoke", "-d", str(missing), "--mode", "mock"])
    assert code == 2


def test_non_loopback_bind_requires_share_secret(monkeypatch) -> None:
    monkeypatch.delenv("SMF_SWARM_SHARE_SECRET", raising=False)
    monkeypatch.delenv("SMF_SWARM_API_TOKEN", raising=False)
    assert is_loopback_bind("127.0.0.1")
    assert not is_loopback_bind("0.0.0.0")
    with pytest.raises(RuntimeError, match="SMF_SWARM_SHARE_SECRET"):
        require_share_secret_for_bind("0.0.0.0")
    monkeypatch.setenv("SMF_SWARM_SHARE_SECRET", "from-env")
    require_share_secret_for_bind("0.0.0.0")
