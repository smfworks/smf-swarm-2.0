"""Capability diagnostic models and engine (TRACE-inspired)."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Protocol


@dataclass
class CapabilityGap:
    name: str
    description: str
    failure_coverage: float
    evidence: List[str] = field(default_factory=list)
    suggested_criterion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TrajectoryFormatter(Protocol):
    def __call__(self, trajectory: Dict[str, Any]) -> str: ...


def default_format_trajectory(trajectory: Dict[str, Any]) -> str:
    if "content" in trajectory:
        return str(trajectory["content"])[:800]
    return json.dumps(trajectory, default=str)[:800]


class CapabilityDiagnosticBackend(Protocol):
    def analyze(
        self,
        successful: List[Dict[str, Any]],
        failed: List[Dict[str, Any]],
        domain: str,
        max_capabilities: int,
    ) -> List[CapabilityGap]: ...


class MockCapabilityBackend:
    """Deterministic offline backend for tests and CI."""

    def analyze(
        self,
        successful: List[Dict[str, Any]],
        failed: List[Dict[str, Any]],
        domain: str,
        max_capabilities: int,
    ) -> List[CapabilityGap]:
        if not failed:
            return []
        n_fail = len(failed)
        # Heuristic: scan failure text for keywords
        blob = " ".join(default_format_trajectory(t).lower() for t in failed)
        gaps: List[CapabilityGap] = []
        rules = [
            (
                "hypothesis prioritization",
                "Select a small number of high-impact hypotheses",
                ["hypothesis", "too many", "breadth"],
                "Does the plan select at most 3 ranked hypotheses?",
            ),
            (
                "executable planning",
                "Produce concrete, executable steps",
                ["vague", "non-executable", "unclear"],
                "Are steps concrete and ordered for execution?",
            ),
            (
                "risk assessment",
                "Surface risks and failure modes",
                ["risk", "no risk", "missing risk"],
                "Is there an explicit risk analysis section?",
            ),
            (
                "evidence grounding",
                "Ground claims in trajectory evidence",
                ["unsupported", "no evidence", "hallucin"],
                "Are claims tied to cited evidence?",
            ),
        ]
        for name, desc, keys, crit in rules:
            hits = sum(1 for k in keys if k in blob)
            if hits == 0 and name != "hypothesis prioritization":
                continue
            coverage = min(0.95, 0.25 + 0.15 * hits + 0.05 * n_fail)
            evidence = [default_format_trajectory(t)[:160] for t in failed[:2]]
            gaps.append(
                CapabilityGap(
                    name=name.title(),
                    description=f"{desc} (domain={domain})",
                    failure_coverage=round(coverage, 3),
                    evidence=evidence,
                    suggested_criterion=crit,
                )
            )
        if not gaps:
            gaps.append(
                CapabilityGap(
                    name="General Reliability",
                    description=f"Broad failure pattern in {domain}",
                    failure_coverage=0.5,
                    evidence=[default_format_trajectory(failed[0])[:160]],
                    suggested_criterion="Does the output meet baseline quality gates?",
                )
            )
        gaps.sort(key=lambda g: g.failure_coverage, reverse=True)
        return gaps[:max_capabilities]


class LLMCapabilityBackend:
    """Optional OpenAI-compatible chat backend."""

    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: float = 60.0,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.timeout = timeout

    def analyze(
        self,
        successful: List[Dict[str, Any]],
        failed: List[Dict[str, Any]],
        domain: str,
        max_capabilities: int,
    ) -> List[CapabilityGap]:
        import httpx

        success_ex = "\n\n".join(
            f"--- Success {i+1} ---\n{default_format_trajectory(t)}"
            for i, t in enumerate(successful[:3])
        )
        fail_ex = "\n\n".join(
            f"--- Failure {i+1} ---\n{default_format_trajectory(t)}"
            for i, t in enumerate(failed[:5])
        )
        prompt = f"""Domain: {domain}

=== SUCCESSFUL TRAJECTORIES ===
{success_ex}

=== FAILED TRAJECTORIES ===
{fail_ex}

Identify up to {max_capabilities} specific missing capabilities that explain failures.
Return ONLY a JSON array of objects with keys:
name, description, failure_coverage (0-1 float), evidence (string array), suggested_criterion.
"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        body = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a capability analyst. Output JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(
                f"{self.base_url}/chat/completions", headers=headers, json=body
            )
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
        return _parse_gaps(content, max_capabilities)


def _parse_gaps(content: str, max_capabilities: int) -> List[CapabilityGap]:
    match = re.search(r"\[.*\]", content, re.DOTALL)
    raw = match.group(0) if match else content
    data = json.loads(raw)
    gaps: List[CapabilityGap] = []
    for item in data[:max_capabilities]:
        gaps.append(
            CapabilityGap(
                name=str(item.get("name", "Unknown")),
                description=str(item.get("description", "")),
                failure_coverage=float(item.get("failure_coverage", 0.0)),
                evidence=list(item.get("evidence") or []),
                suggested_criterion=str(item.get("suggested_criterion", "")),
            )
        )
    gaps.sort(key=lambda g: g.failure_coverage, reverse=True)
    return gaps


class CapabilityDiagnostic:
    """Platform capability diagnostic (governance-agnostic core)."""

    def __init__(
        self,
        backend: Optional[CapabilityDiagnosticBackend] = None,
        max_capabilities: int = 8,
    ) -> None:
        self.backend = backend or MockCapabilityBackend()
        self.max_capabilities = max_capabilities

    def diagnose(
        self,
        successful_trajectories: List[Dict[str, Any]],
        failed_trajectories: List[Dict[str, Any]],
        domain: str = "general",
    ) -> List[CapabilityGap]:
        if not failed_trajectories:
            return []
        return self.backend.analyze(
            successful_trajectories,
            failed_trajectories,
            domain,
            self.max_capabilities,
        )
