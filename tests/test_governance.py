"""Tests for governance hooks."""
from pathlib import Path

import pytest

from smf_swarm.governance import (
    AuditLog,
    IdentityRegistry,
    PermissionDenied,
    PermissionEngine,
)


def test_identity_register_and_deactivate():
    reg = IdentityRegistry()
    a = reg.register("Aiona", agent_id="aiona")
    assert a.agent_id == "aiona"
    assert a.active
    reg.deactivate("aiona")
    with pytest.raises(PermissionError):
        reg.require_active("aiona")


def test_audit_hash_chain(tmp_path: Path):
    log = AuditLog(path=tmp_path / "audit.jsonl")
    log.append(agent_id="a", action="t1", resource="r", outcome="success")
    log.append(agent_id="a", action="t2", resource="r", outcome="success")
    assert log.verify_chain()
    assert len(log) == 2
    # reload
    log2 = AuditLog(path=tmp_path / "audit.jsonl")
    assert len(log2) == 2
    assert log2.verify_chain()


def test_permission_deny_by_default():
    reg = IdentityRegistry()
    audit = AuditLog()
    pe = PermissionEngine(identities=reg, audit=audit)
    reg.register("Bot", agent_id="bot")
    assert pe.check("bot", "capability.diagnose") is False
    with pytest.raises(PermissionDenied):
        pe.require("bot", "capability.diagnose")
    pe.grant("bot", "capability.diagnose")
    assert pe.check("bot", "capability.diagnose") is True
