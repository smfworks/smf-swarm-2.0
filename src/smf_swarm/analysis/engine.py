"""Predictive multi-persona swarm analysis engine."""
from __future__ import annotations

import csv
import io
import json
import math
import re
import statistics
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


@dataclass
class Attachment:
    filename: str
    content_type: str
    text: str
    size_bytes: int = 0

    def preview(self, n: int = 4000) -> str:
        return self.text[:n]


@dataclass
class PersonaView:
    persona: str
    role: str
    findings: List[str] = field(default_factory=list)
    confidence: float = 0.5


@dataclass
class PredictiveReport:
    run_id: str
    question: str
    created_at: str
    mode: str  # mock | llm
    executive_summary: str
    prediction: str
    confidence: float
    time_horizon: str
    key_drivers: List[str]
    scenarios: List[Dict[str, str]]
    risks: List[str]
    data_insights: List[str]
    recommended_actions: List[str]
    persona_views: List[PersonaView]
    attachments_used: List[str]
    audit_events: int = 0
    chain_valid: bool = False
    agent_id: str = ""
    disclaimer: str = (
        "Decision support only — not professional advice. "
        "Validate with domain experts and primary data."
    )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


def extract_text_from_bytes(filename: str, data: bytes, content_type: str = "") -> str:
    name = filename.lower()
    if name.endswith(".csv") or "csv" in content_type:
        try:
            text = data.decode("utf-8", errors="replace")
            return _summarize_csv(text)
        except Exception:
            return data.decode("utf-8", errors="replace")[:20000]
    if name.endswith(".json") or "json" in content_type:
        try:
            obj = json.loads(data.decode("utf-8", errors="replace"))
            return json.dumps(obj, indent=2)[:20000]
        except Exception:
            return data.decode("utf-8", errors="replace")[:20000]
    # plain / md / other text
    return data.decode("utf-8", errors="replace")[:20000]


def _summarize_csv(text: str) -> str:
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return "Empty CSV"
    header = rows[0]
    body = rows[1:]
    lines = [
        f"CSV columns ({len(header)}): {', '.join(header[:20])}",
        f"Row count (data): {len(body)}",
    ]
    # numeric column stats
    for col_i, col in enumerate(header[:12]):
        vals: List[float] = []
        for r in body:
            if col_i >= len(r):
                continue
            try:
                vals.append(float(str(r[col_i]).replace(",", "").strip()))
            except ValueError:
                continue
        if len(vals) >= 3:
            lines.append(
                f"  {col}: n={len(vals)} mean={statistics.mean(vals):.4g} "
                f"stdev={statistics.pstdev(vals):.4g} "
                f"min={min(vals):.4g} max={max(vals):.4g}"
            )
    # sample rows
    lines.append("Sample rows:")
    for r in body[:5]:
        lines.append("  " + " | ".join(r[:8]))
    return "\n".join(lines)


def _keywords(text: str) -> List[str]:
    stop = {
        "the", "and", "for", "with", "that", "this", "from", "will", "have",
        "what", "when", "where", "which", "into", "about", "your", "their",
    }
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{3,}", text.lower())
    freq: Dict[str, int] = {}
    for w in words:
        if w in stop:
            continue
        freq[w] = freq.get(w, 0) + 1
    ranked = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
    return [w for w, _ in ranked[:12]]


class MockPredictiveBackend:
    """Offline multi-persona analysis (no network)."""

    def analyze(
        self, question: str, attachments: Sequence[Attachment]
    ) -> Dict[str, Any]:
        blob = question + "\n" + "\n".join(a.text for a in attachments)
        keys = _keywords(blob)
        has_numeric = any(
            "mean=" in a.text or re.search(r"\d+\.\d+", a.text) for a in attachments
        )
        data_insights: List[str] = []
        for a in attachments:
            data_insights.append(f"{a.filename}: {len(a.text)} chars ingested")
            if "CSV columns" in a.text:
                data_insights.append(a.text.splitlines()[0])
                for line in a.text.splitlines():
                    if "mean=" in line:
                        data_insights.append(line.strip())
                        break
        if not attachments:
            data_insights.append("No files attached — analysis is question-only.")

        drivers = keys[:5] or ["stated objectives", "available evidence", "uncertainty"]
        conf = 0.42
        if attachments:
            conf += 0.12
        if has_numeric:
            conf += 0.15
        if len(question) > 40:
            conf += 0.05
        conf = min(0.88, conf)

        # Directional prediction heuristic
        q = question.lower()
        if any(w in q for w in ("risk", "fail", "decline", "drop", "threat")):
            direction = "elevated downside risk relative to baseline"
        elif any(w in q for w in ("grow", "increas", "opportunit", "upside", "win")):
            direction = "moderate upside if key drivers hold"
        else:
            direction = "mixed outcomes; base case is continuity with variance"

        prediction = (
            f"Based on the question and {len(attachments)} attachment(s), "
            f"the swarm base-case outlook is **{direction}**. "
            f"Most salient themes: {', '.join(drivers[:4])}."
        )

        scenarios = [
            {
                "name": "Base case",
                "probability": "~45–55%",
                "narrative": (
                    "Current patterns continue; incremental change driven by "
                    f"{drivers[0] if drivers else 'existing trends'}."
                ),
            },
            {
                "name": "Upside",
                "probability": "~20–30%",
                "narrative": (
                    "Favorable alignment of drivers; faster realization of "
                    "stated goals if risks are actively managed."
                ),
            },
            {
                "name": "Downside",
                "probability": "~20–30%",
                "narrative": (
                    "Key assumptions break (data gaps, execution risk, or "
                    "external shock); outcomes worse than baseline."
                ),
            },
        ]

        risks = [
            "Incomplete or biased attached data may skew conclusions.",
            "Mock/offline mode uses heuristics — not a statistical forecast model.",
            "Single-question framing can hide multi-objective tradeoffs.",
        ]
        if not attachments:
            risks.insert(0, "No supporting data attached — confidence capped.")

        actions = [
            "Validate the top drivers against primary sources or stakeholders.",
            "Add longitudinal data (time series) if the question is time-sensitive.",
            "Run a second pass with LLM mode when an endpoint is available for richer synthesis.",
            "Assign owners to the top 2 recommended actions this week.",
        ]

        personas = [
            PersonaView(
                persona="Scout",
                role="Evidence extraction",
                findings=data_insights[:6] or ["No structured evidence extracted."],
                confidence=0.55 if attachments else 0.35,
            ),
            PersonaView(
                persona="Strategist",
                role="Scenario design",
                findings=[s["name"] + ": " + s["narrative"][:120] for s in scenarios],
                confidence=conf * 0.9,
            ),
            PersonaView(
                persona="Skeptic",
                role="Risk & confounds",
                findings=risks,
                confidence=0.6,
            ),
            PersonaView(
                persona="Forecaster",
                role="Prediction synthesis",
                findings=[prediction, f"Confidence score: {conf:.0%}"],
                confidence=conf,
            ),
        ]

        summary = (
            f"Swarm analysis of your question with {len(attachments)} file(s). "
            f"Base-case confidence ~{conf:.0%}. "
            f"Focus next on: {', '.join(drivers[:3])}."
        )

        return {
            "executive_summary": summary,
            "prediction": prediction,
            "confidence": round(conf, 3),
            "time_horizon": "near-term (weeks–months) unless data implies otherwise",
            "key_drivers": drivers,
            "scenarios": scenarios,
            "risks": risks,
            "data_insights": data_insights,
            "recommended_actions": actions,
            "persona_views": personas,
        }


class LLMPredictiveBackend:
    """Optional OpenAI-compatible multi-persona synthesis."""

    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: str = "",
        timeout: float = 120.0,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def analyze(
        self, question: str, attachments: Sequence[Attachment]
    ) -> Dict[str, Any]:
        import httpx

        att_block = "\n\n".join(
            f"### File: {a.filename}\n{a.preview(6000)}" for a in attachments
        ) or "(no attachments)"
        prompt = f"""You are a predictive analysis swarm (Scout, Strategist, Skeptic, Forecaster).

QUESTION:
{question}

ATTACHED DATA:
{att_block}

Return ONLY JSON with keys:
executive_summary (string),
prediction (string),
confidence (0-1 number),
time_horizon (string),
key_drivers (string array),
scenarios (array of {{name, probability, narrative}}),
risks (string array),
data_insights (string array),
recommended_actions (string array),
persona_views (array of {{persona, role, findings (string array), confidence (0-1)}})
"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        body = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You produce rigorous predictive decision support as JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 2500,
        }
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(
                f"{self.base_url}/chat/completions", headers=headers, json=body
            )
            r.raise_for_status()
            msg = r.json()["choices"][0]["message"]
            content = msg.get("content") or msg.get("reasoning") or ""
        return _parse_llm_report(content)


def _parse_llm_report(content: str) -> Dict[str, Any]:
    text = content.strip()
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError("no JSON object in LLM response")
    data = json.loads(m.group(0))
    personas = []
    for p in data.get("persona_views") or []:
        if isinstance(p, dict):
            personas.append(
                PersonaView(
                    persona=str(p.get("persona", "Analyst")),
                    role=str(p.get("role", "")),
                    findings=list(p.get("findings") or []),
                    confidence=float(p.get("confidence") or 0.5),
                )
            )
    data["persona_views"] = personas
    return data


class PredictiveSwarmEngine:
    """Governed predictive analysis entrypoint."""

    def __init__(
        self,
        *,
        mode: str = "mock",
        audit_path: Optional[str | Path] = None,
        llm_model: Optional[str] = None,
        llm_base_url: Optional[str] = None,
        llm_api_key: str = "",
        agent_name: str = "swarm-predictive-ui",
    ) -> None:
        from smf_swarm.governance import AuditLog, IdentityRegistry, PermissionEngine
        from smf_swarm.pipeline.phase1_run import CAPABILITY_DIAGNOSE

        self.mode = mode if mode in ("mock", "llm") else "mock"
        self.identities = IdentityRegistry()
        self.audit = AuditLog(path=audit_path)
        self.permissions = PermissionEngine(
            identities=self.identities, audit=self.audit, open_mode=False
        )
        self.agent = self.identities.register(agent_name, agent_id="swarm-app-user")
        # Reuse capability name for analysis runs (app-level permission)
        self.CAP = "analysis.predict"
        self.permissions.grants.setdefault(self.agent.agent_id, set()).add(self.CAP)
        self.audit.append(
            agent_id=self.agent.agent_id,
            action="identity.register",
            resource=self.agent.agent_id,
            outcome="success",
            details={"app": "predictive"},
        )
        self.audit.append(
            agent_id=self.agent.agent_id,
            action="permission.grant",
            resource=self.CAP,
            outcome="success",
            details={},
        )

        if self.mode == "llm":
            self.backend = LLMPredictiveBackend(
                model=llm_model or "unsloth/Qwen3.6-35B-A3B-NVFP4",
                base_url=llm_base_url or "http://spark-56bc:8888/v1",
                api_key=llm_api_key or "not-needed",
            )
        else:
            self.backend = MockPredictiveBackend()

    def run(
        self,
        question: str,
        attachments: Optional[Sequence[Attachment]] = None,
    ) -> PredictiveReport:
        import uuid

        attachments = list(attachments or [])
        q = (question or "").strip()
        if not q:
            raise ValueError("question is required")

        if not self.permissions.check(self.agent.agent_id, self.CAP, resource="predict"):
            raise PermissionError("analysis.predict denied")

        self.audit.append(
            agent_id=self.agent.agent_id,
            action="analysis.start",
            resource="predict",
            outcome="success",
            details={
                "mode": self.mode,
                "n_attachments": len(attachments),
                "question_len": len(q),
            },
        )

        try:
            raw = self.backend.analyze(q, attachments)
        except Exception as e:
            self.audit.append(
                agent_id=self.agent.agent_id,
                action="analysis.complete",
                resource="predict",
                outcome="failure",
                details={"error": str(e)},
            )
            # Fallback to mock if LLM fails
            if self.mode == "llm":
                raw = MockPredictiveBackend().analyze(q, attachments)
                self.mode = "mock"
            else:
                raise

        personas = raw.get("persona_views") or []
        if personas and isinstance(personas[0], dict):
            personas = [
                PersonaView(
                    persona=str(p.get("persona", "Analyst")),
                    role=str(p.get("role", "")),
                    findings=list(p.get("findings") or []),
                    confidence=float(p.get("confidence") or 0.5),
                )
                for p in personas
            ]

        report = PredictiveReport(
            run_id=uuid.uuid4().hex[:12],
            question=q,
            created_at=datetime.now(timezone.utc).isoformat(),
            mode=self.mode,
            executive_summary=str(raw.get("executive_summary", "")),
            prediction=str(raw.get("prediction", "")),
            confidence=float(raw.get("confidence") or 0.5),
            time_horizon=str(raw.get("time_horizon", "")),
            key_drivers=list(raw.get("key_drivers") or []),
            scenarios=list(raw.get("scenarios") or []),
            risks=list(raw.get("risks") or []),
            data_insights=list(raw.get("data_insights") or []),
            recommended_actions=list(raw.get("recommended_actions") or []),
            persona_views=list(personas),
            attachments_used=[a.filename for a in attachments],
            audit_events=len(self.audit),
            chain_valid=self.audit.verify_chain(),
            agent_id=self.agent.agent_id,
        )

        self.audit.append(
            agent_id=self.agent.agent_id,
            action="analysis.complete",
            resource="predict",
            outcome="success",
            details={
                "run_id": report.run_id,
                "confidence": report.confidence,
                "mode": report.mode,
            },
        )
        report.audit_events = len(self.audit)
        report.chain_valid = self.audit.verify_chain()
        return report
