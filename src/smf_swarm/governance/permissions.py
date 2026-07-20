"""Capability permission engine (Phase 1 governance hook)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Set

from .audit import AuditLog
from .identity import IdentityRegistry


class PermissionDenied(Exception):
    def __init__(self, agent_id: str, capability: str, reason: str = "not granted"):
        self.agent_id = agent_id
        self.capability = capability
        self.reason = reason
        super().__init__(f"Permission denied: {agent_id} cannot {capability} ({reason})")


@dataclass
class PermissionEngine:
    """Simple allowlist: agent_id -> set of capability names.

    Default: empty allowlist (deny by default) unless open_mode=True for dev.
    """

    identities: IdentityRegistry
    audit: AuditLog
    grants: Dict[str, Set[str]] = field(default_factory=dict)
    open_mode: bool = False

    def grant(self, agent_id: str, capability: str) -> None:
        self.identities.require_active(agent_id)
        self.grants.setdefault(agent_id, set()).add(capability)
        self.audit.append(
            agent_id=agent_id,
            action="permission.grant",
            resource=capability,
            outcome="success",
            details={"capability": capability},
        )

    def revoke(self, agent_id: str, capability: str) -> None:
        if agent_id in self.grants:
            self.grants[agent_id].discard(capability)
        self.audit.append(
            agent_id=agent_id,
            action="permission.revoke",
            resource=capability,
            outcome="success",
            details={"capability": capability},
        )

    def check(self, agent_id: str, capability: str, resource: str = "") -> bool:
        """Return True if allowed; always audits."""
        try:
            self.identities.require_active(agent_id)
        except (KeyError, PermissionError) as e:
            self.audit.append(
                agent_id=agent_id,
                action="permission.check",
                resource=resource or capability,
                outcome="denied",
                details={"capability": capability, "reason": str(e)},
            )
            return False

        allowed = self.open_mode or capability in self.grants.get(agent_id, set())
        self.audit.append(
            agent_id=agent_id,
            action="permission.check",
            resource=resource or capability,
            outcome="allowed" if allowed else "denied",
            details={"capability": capability},
        )
        return allowed

    def require(self, agent_id: str, capability: str, resource: str = "") -> None:
        if not self.check(agent_id, capability, resource=resource):
            raise PermissionDenied(agent_id, capability)
