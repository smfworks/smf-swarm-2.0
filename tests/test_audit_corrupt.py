"""Corrupt audit JSONL must not crash the process."""
from __future__ import annotations

from pathlib import Path

from smf_swarm.governance import AuditLog


def test_audit_skips_truncated_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    log = AuditLog(path=path)
    log.append(agent_id="a", action="ok1", resource="r", outcome="success")
    with path.open("a", encoding="utf-8") as fh:
        fh.write("{not-json\n")
        fh.write('{"event_id": "x"\n')
    log.append(agent_id="a", action="ok2", resource="r", outcome="success")

    reloaded = AuditLog(path=path)
    actions = [ev.action for ev in reloaded.events()]
    assert "ok1" in actions
    assert "ok2" in actions
    assert reloaded.verify_chain()
