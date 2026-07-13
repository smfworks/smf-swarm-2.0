"""Append-only hash-chained audit log (Phase 1 governance hook)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


@dataclass
class AuditEvent:
    event_id: str
    timestamp: str
    agent_id: str
    action: str
    resource: str
    outcome: str  # allowed | denied | success | failure
    details: Dict[str, Any] = field(default_factory=dict)
    prev_hash: str = ""
    event_hash: str = ""

    def compute_hash(self) -> str:
        payload = {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "agent_id": self.agent_id,
            "action": self.action,
            "resource": self.resource,
            "outcome": self.outcome,
            "details": self.details,
            "prev_hash": self.prev_hash,
        }
        return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


class AuditLog:
    """Hash-chained audit log with optional JSONL persistence."""

    def __init__(self, path: Optional[str | Path] = None) -> None:
        self.path = Path(path) if path else None
        self._events: List[AuditEvent] = []
        self._last_hash = "0" * 64
        if self.path and self.path.exists():
            self._load()

    def _load(self) -> None:
        assert self.path is not None
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            data = json.loads(line)
            ev = AuditEvent(**data)
            self._events.append(ev)
            self._last_hash = ev.event_hash

    def append(
        self,
        *,
        agent_id: str,
        action: str,
        resource: str,
        outcome: str,
        details: Optional[Dict[str, Any]] = None,
        event_id: Optional[str] = None,
    ) -> AuditEvent:
        import uuid

        ev = AuditEvent(
            event_id=event_id or uuid.uuid4().hex,
            timestamp=_utcnow_iso(),
            agent_id=agent_id,
            action=action,
            resource=resource,
            outcome=outcome,
            details=dict(details or {}),
            prev_hash=self._last_hash,
        )
        ev.event_hash = ev.compute_hash()
        self._events.append(ev)
        self._last_hash = ev.event_hash
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(_canonical(asdict(ev)) + "\n")
        return ev

    def verify_chain(self) -> bool:
        prev = "0" * 64
        for ev in self._events:
            if ev.prev_hash != prev:
                return False
            if ev.compute_hash() != ev.event_hash:
                return False
            prev = ev.event_hash
        return True

    def events(self) -> List[AuditEvent]:
        return list(self._events)

    def __len__(self) -> int:
        return len(self._events)
