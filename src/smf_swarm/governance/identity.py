"""Agent identity hooks (Phase 1: stable IDs; crypto-ready shape)."""
from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class AgentIdentity:
    """Stable agent identity.

    Phase 1: UUID + optional public key placeholder.
    Phase 2: bind to HBHC / real cryptographic credentials.
    """

    agent_id: str
    display_name: str
    created_at: datetime
    public_key_pem: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)
    active: bool = True

    def principal(self) -> str:
        return self.agent_id


class IdentityRegistry:
    """In-process identity store. Replace with durable store later."""

    def __init__(self) -> None:
        self._agents: Dict[str, AgentIdentity] = {}

    def register(
        self,
        display_name: str,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> AgentIdentity:
        aid = agent_id or f"agent_{uuid.uuid4().hex[:12]}"
        if aid in self._agents:
            raise ValueError(f"agent already registered: {aid}")
        # Placeholder "key material" proves interface for future crypto
        key_placeholder = f"pk_pending_{secrets.token_hex(8)}"
        ident = AgentIdentity(
            agent_id=aid,
            display_name=display_name,
            created_at=_utcnow(),
            public_key_pem=key_placeholder,
            metadata=dict(metadata or {}),
            active=True,
        )
        self._agents[aid] = ident
        return ident

    def get(self, agent_id: str) -> Optional[AgentIdentity]:
        return self._agents.get(agent_id)

    def require_active(self, agent_id: str) -> AgentIdentity:
        ident = self.get(agent_id)
        if not ident:
            raise KeyError(f"unknown agent: {agent_id}")
        if not ident.active:
            raise PermissionError(f"agent inactive: {agent_id}")
        return ident

    def deactivate(self, agent_id: str) -> None:
        ident = self.require_active(agent_id)
        self._agents[agent_id] = AgentIdentity(
            agent_id=ident.agent_id,
            display_name=ident.display_name,
            created_at=ident.created_at,
            public_key_pem=ident.public_key_pem,
            metadata=ident.metadata,
            active=False,
        )

    def list_active(self) -> list[AgentIdentity]:
        return [a for a in self._agents.values() if a.active]
