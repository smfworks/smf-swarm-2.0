"""Phase 1 pipeline: identity + permission + diagnostic + audit."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from smf_swarm.capability import CapabilityDiagnostic, CapabilityGap, MockCapabilityBackend
from smf_swarm.governance import (
    AuditLog,
    IdentityRegistry,
    PermissionDenied,
    PermissionEngine,
)

CAPABILITY_DIAGNOSE = "capability.diagnose"


@dataclass
class Phase1Result:
    agent_id: str
    domain: str
    gaps: List[CapabilityGap] = field(default_factory=list)
    audit_events: int = 0
    chain_valid: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "domain": self.domain,
            "gaps": [g.to_dict() for g in self.gaps],
            "audit_events": self.audit_events,
            "chain_valid": self.chain_valid,
        }


class Phase1Pipeline:
    """Governed capability diagnosis entrypoint."""

    def __init__(
        self,
        *,
        audit_path: Optional[str | Path] = None,
        diagnostic: Optional[CapabilityDiagnostic] = None,
    ) -> None:
        self.identities = IdentityRegistry()
        self.audit = AuditLog(path=audit_path)
        self.permissions = PermissionEngine(
            identities=self.identities, audit=self.audit, open_mode=False
        )
        self.diagnostic = diagnostic or CapabilityDiagnostic(
            backend=MockCapabilityBackend()
        )

    def bootstrap_agent(
        self, display_name: str, agent_id: Optional[str] = None
    ) -> str:
        ident = self.identities.register(display_name, agent_id=agent_id)
        self.audit.append(
            agent_id=ident.agent_id,
            action="identity.register",
            resource=ident.agent_id,
            outcome="success",
            details={"display_name": display_name},
        )
        self.permissions.grant(ident.agent_id, CAPABILITY_DIAGNOSE)
        return ident.agent_id

    def run_diagnosis(
        self,
        agent_id: str,
        successful: List[Dict[str, Any]],
        failed: List[Dict[str, Any]],
        domain: str = "general",
    ) -> Phase1Result:
        self.permissions.require(agent_id, CAPABILITY_DIAGNOSE, resource=domain)
        self.audit.append(
            agent_id=agent_id,
            action="diagnostic.start",
            resource=domain,
            outcome="success",
            details={
                "n_success": len(successful),
                "n_failed": len(failed),
            },
        )
        try:
            gaps = self.diagnostic.diagnose(successful, failed, domain=domain)
            self.audit.append(
                agent_id=agent_id,
                action="diagnostic.complete",
                resource=domain,
                outcome="success",
                details={"n_gaps": len(gaps), "top": [g.name for g in gaps[:3]]},
            )
        except Exception as e:
            self.audit.append(
                agent_id=agent_id,
                action="diagnostic.complete",
                resource=domain,
                outcome="failure",
                details={"error": str(e)},
            )
            raise

        return Phase1Result(
            agent_id=agent_id,
            domain=domain,
            gaps=gaps,
            audit_events=len(self.audit),
            chain_valid=self.audit.verify_chain(),
        )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="SMF Swarm Phase 1 diagnosis")
    parser.add_argument("--agent-name", default="phase1-diagnostic-agent")
    parser.add_argument("--domain", default="article_editing")
    parser.add_argument("--audit", default="")
    parser.add_argument("--fixture", default="", help="JSON file with success/failed lists")
    args = parser.parse_args(argv)

    if args.fixture:
        data = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
        successful = data.get("successful", [])
        failed = data.get("failed", [])
    else:
        successful = [
            {"content": "Selected 2 high-impact hypotheses. Clear risks. Executable plan."},
            {"content": "Prioritized structure over formatting. Good dependency analysis."},
        ]
        failed = [
            {"content": "Selected 6 hypotheses including minor formatting. No risk analysis."},
            {"content": "Tried to fix everything at once. Plan was vague and non-executable."},
            {"content": "Included low-impact changes while missing core argument weaknesses."},
        ]

    pipe = Phase1Pipeline(audit_path=args.audit or None)
    agent_id = pipe.bootstrap_agent(args.agent_name)
    result = pipe.run_diagnosis(agent_id, successful, failed, domain=args.domain)
    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.chain_valid else 1


if __name__ == "__main__":
    sys.exit(main())
