"""Predictive multi-persona swarm analysis engine (v0.3 product quality)."""
from __future__ import annotations

import csv
import io
import json
import re
import statistics
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


@dataclass
class Attachment:
    filename: str
    content_type: str
    text: str
    size_bytes: int = 0
    charts: List[Any] = field(default_factory=list)

    def preview(self, n: int = 4000) -> str:
        return self.text[:n]


@dataclass
class PersonaView:
    persona: str
    role: str
    findings: List[str] = field(default_factory=list)
    confidence: float = 0.5


@dataclass
class EvidenceItem:
    source: str
    excerpt: str
    claim: str
    kind: str = "attachment"  # attachment | derived | question


@dataclass
class PredictiveReport:
    run_id: str
    question: str
    created_at: str
    mode: str  # mock | llm
    executive_summary: str
    prediction: str
    prediction_headline: str
    prediction_detail: str
    confidence: float
    time_horizon: str
    key_drivers: List[str]
    scenarios: List[Dict[str, Any]]
    risks: List[str]
    data_insights: List[str]
    recommended_actions: List[str]
    persona_views: List[PersonaView]
    evidence: List[EvidenceItem]
    attachments_used: List[str]
    methodology: Dict[str, Any]
    charts: List[Dict[str, Any]] = field(default_factory=list)
    share_id: str = ""
    share_path: str = ""
    model_used: str = ""
    fallback_used: bool = False
    audit_events: int = 0
    chain_valid: bool = False
    agent_id: str = ""
    disclaimer: str = (
        "Decision support only — not professional advice. "
        "Validate with domain experts and primary data."
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_markdown(self) -> str:
        lines = [
            f"# SMF Swarm Analysis Report",
            f"",
            f"**Run:** `{self.run_id}`  ",
            f"**When:** {self.created_at}  ",
            f"**Mode:** {self.mode}"
            + (f" (fallback from LLM)" if self.fallback_used else "")
            + "  ",
            f"**Confidence:** {self.confidence:.0%}  ",
            f"**Horizon:** {self.time_horizon}  ",
            f"",
            f"## Question",
            f"",
            self.question,
            f"",
            f"## Prediction",
            f"",
            f"**{self.prediction_headline or self.prediction}**",
            f"",
            self.prediction_detail or self.prediction,
            f"",
            f"## Executive summary",
            f"",
            self.executive_summary,
            f"",
            f"## Key drivers",
            f"",
        ]
        for d in self.key_drivers:
            lines.append(f"- {d}")
        lines += ["", "## Scenarios", ""]
        for s in self.scenarios:
            lines.append(
                f"- **{s.get('name', '')}** ({_fmt_prob(s.get('probability'))}): "
                f"{s.get('narrative', '')}"
            )
        lines += ["", "## Evidence", ""]
        for e in self.evidence:
            lines.append(f"- **[{e.source}]** {e.claim} — _{e.excerpt[:200]}_")
        lines += ["", "## Charts", ""]
        if self.charts:
            for c in self.charts:
                name = c.get("name", "series") if isinstance(c, dict) else getattr(c, "name", "series")
                fn = c.get("filename", "") if isinstance(c, dict) else getattr(c, "filename", "")
                stats = c.get("stats", {}) if isinstance(c, dict) else getattr(c, "stats", {})
                lines.append(
                    f"- **{fn}:{name}** n={stats.get('n', '?')} "
                    f"last={stats.get('last', '?')} Δ={stats.get('delta', '?')}"
                )
        else:
            lines.append("- No numeric series charts")
        lines += ["", "## Risks", ""]
        for r in self.risks:
            lines.append(f"- {r}")
        lines += ["", "## Recommended actions", ""]
        for a in self.recommended_actions:
            lines.append(f"- {a}")
        lines += ["", "## Methodology", ""]
        m = self.methodology or {}
        lines.append(f"- Personas: {', '.join(m.get('personas') or [])}")
        lines.append(f"- Pipeline: {m.get('pipeline', '')}")
        lines.append(f"- Model: {self.model_used or m.get('model', 'n/a')}")
        lines.append(f"- Limitations: {m.get('limitations', '')}")
        lines += ["", f"_{self.disclaimer}_", ""]
        return "\n".join(lines)


def _fmt_prob(p: Any) -> str:
    if p is None:
        return ""
    if isinstance(p, (int, float)):
        v = float(p)
        if v <= 1.0:
            return f"{v:.0%}"
        return f"{v:.0f}%"
    s = str(p).strip()
    if re.fullmatch(r"0?\.\d+", s):
        return f"{float(s):.0%}"
    if re.fullmatch(r"\d+(\.\d+)?", s):
        v = float(s)
        if v <= 1:
            return f"{v:.0%}"
        if v <= 100:
            return f"{v:.0f}%"
    return s


def normalize_scenarios(scenarios: Sequence[Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for s in scenarios or []:
        if not isinstance(s, dict):
            continue
        out.append(
            {
                "name": str(s.get("name", "Scenario")),
                "probability": _fmt_prob(s.get("probability")),
                "probability_raw": s.get("probability"),
                "narrative": str(s.get("narrative", "")),
            }
        )
    return out


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
    lines.append("Sample rows:")
    for r in body[:5]:
        lines.append("  " + " | ".join(r[:8]))
    return "\n".join(lines)


def _keywords(text: str) -> List[str]:
    stop = {
        "the", "and", "for", "with", "that", "this", "from", "will", "have",
        "what", "when", "where", "which", "into", "about", "your", "their",
        "over", "past", "above", "below", "than", "this", "week", "month",
    }
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{3,}", text.lower())
    freq: Dict[str, int] = {}
    for w in words:
        if w in stop:
            continue
        freq[w] = freq.get(w, 0) + 1
    ranked = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
    return [w for w, _ in ranked[:12]]


def build_evidence(
    question: str, attachments: Sequence[Attachment], data_insights: Sequence[str]
) -> List[EvidenceItem]:
    items: List[EvidenceItem] = []
    items.append(
        EvidenceItem(
            source="question",
            excerpt=question[:240],
            claim="User decision / forecasting question",
            kind="question",
        )
    )
    for a in attachments:
        lines = [ln.strip() for ln in a.text.splitlines() if ln.strip()]
        # Prefer numeric / stat lines
        picks = [ln for ln in lines if re.search(r"\d", ln)][:4]
        if not picks:
            picks = lines[:2]
        for ln in picks:
            items.append(
                EvidenceItem(
                    source=a.filename,
                    excerpt=ln[:280],
                    claim=f"Observed signal in {a.filename}",
                    kind="attachment",
                )
            )
    for insight in list(data_insights)[:5]:
        if any(insight[:40] in e.excerpt for e in items):
            continue
        items.append(
            EvidenceItem(
                source="derived",
                excerpt=str(insight)[:280],
                claim="Derived insight from attached data",
                kind="derived",
            )
        )
    return items[:16]


def split_prediction(prediction: str, question: str) -> Tuple[str, str]:
    """Turn short answers like 'No' into headline + detail."""
    p = (prediction or "").strip()
    if not p:
        return "Inconclusive", "Insufficient signal to form a clear prediction."
    # If short yes/no style
    first = p.split("\n")[0].strip().strip("*").strip()
    if len(first) <= 24 and re.match(
        r"^(yes|no|likely|unlikely|maybe|uncertain|mixed)([.!]|$)",
        first,
        re.I,
    ):
        headline = first.rstrip(".!")
        detail = (
            f"Regarding: “{question[:180]}” — the swarm base-case answer is "
            f"**{headline}**. {p[len(first):].strip()}".strip()
        )
        if detail == f"Regarding: “{question[:180]}” — the swarm base-case answer is **{headline}**.":
            detail += " See executive summary, scenarios, and evidence for the full rationale."
        return headline, detail
    # Use first sentence as headline if long
    parts = re.split(r"(?<=[.!?])\s+", p, maxsplit=1)
    if len(parts[0]) <= 120:
        return parts[0], p
    return parts[0][:100] + "…", p


class MockPredictiveBackend:
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
                        data_insights.append(f"[{a.filename}] {line.strip()}")
                        break
            else:
                for line in a.text.splitlines()[:3]:
                    if re.search(r"\d", line):
                        data_insights.append(f"[{a.filename}] {line.strip()[:160]}")
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

        q = question.lower()
        if any(w in q for w in ("risk", "fail", "decline", "drop", "threat", "fall")):
            headline = "Unlikely / elevated downside"
            direction = "elevated downside risk relative to baseline"
        elif any(w in q for w in ("grow", "increas", "opportunit", "upside", "win", "rise", "above")):
            headline = "Possible but not base case"
            direction = "moderate upside only if key drivers flip favorably"
        else:
            headline = "Mixed / continuity base case"
            direction = "mixed outcomes; base case is continuity with variance"

        prediction = (
            f"Based on the question and {len(attachments)} attachment(s), "
            f"the swarm base-case outlook is **{direction}**. "
            f"Most salient themes: {', '.join(drivers[:4])}."
        )
        scenarios = [
            {
                "name": "Base case",
                "probability": 0.5,
                "narrative": (
                    "Current patterns continue; incremental change driven by "
                    f"{drivers[0] if drivers else 'existing trends'}."
                ),
            },
            {
                "name": "Upside",
                "probability": 0.25,
                "narrative": (
                    "Favorable alignment of drivers; faster realization of "
                    "stated goals if risks are actively managed."
                ),
            },
            {
                "name": "Downside",
                "probability": 0.25,
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
            "prediction_headline": headline,
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

Return ONLY one JSON object with keys:
executive_summary (string),
prediction (string — full sentence answer, not just Yes/No),
prediction_headline (short label e.g. "No" or "Likely upside"),
confidence (0-1 number),
time_horizon (string),
key_drivers (string array),
scenarios (array of {{name, probability as 0-1 number, narrative}}),
risks (string array),
data_insights (string array — cite file names where possible),
evidence (array of {{source, excerpt, claim}}),
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
                    "content": (
                        "You produce rigorous predictive decision support as JSON only. "
                        "Cite attached data. Use probability numbers 0-1 for scenarios."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 3500,
        }
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(
                f"{self.base_url}/chat/completions", headers=headers, json=body
            )
            r.raise_for_status()
            msg = r.json()["choices"][0]["message"]
            content = msg.get("content") or ""
            reasoning = msg.get("reasoning") or msg.get("reasoning_content") or ""
            text = content.strip() if content and str(content).strip() else reasoning
        return _parse_llm_report(text)


def _parse_llm_report(content: str) -> Dict[str, Any]:
    text = re.sub(r"<think>[\s\S]*?</think>", "", content or "", flags=re.I).strip()
    if not text:
        raise ValueError("empty LLM content")
    data = None
    last_err: Optional[Exception] = None
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            data, _ = json.JSONDecoder().raw_decode(text[i:])
            if isinstance(data, dict):
                break
        except json.JSONDecodeError as e:
            last_err = e
            continue
    if not isinstance(data, dict):
        raise ValueError(f"no JSON object in LLM response: {last_err}")

    personas = []
    for p in data.get("persona_views") or []:
        if isinstance(p, dict):
            conf = p.get("confidence", 0.5)
            try:
                conf_f = float(conf)
            except (TypeError, ValueError):
                conf_f = 0.5
            personas.append(
                PersonaView(
                    persona=str(p.get("persona", "Analyst")),
                    role=str(p.get("role", "")),
                    findings=list(p.get("findings") or [])
                    if isinstance(p.get("findings"), list)
                    else [str(p.get("findings") or "")],
                    confidence=conf_f,
                )
            )
    data["persona_views"] = personas

    # evidence optional
    ev = []
    for e in data.get("evidence") or []:
        if isinstance(e, dict):
            ev.append(
                EvidenceItem(
                    source=str(e.get("source", "unknown")),
                    excerpt=str(e.get("excerpt", ""))[:400],
                    claim=str(e.get("claim", "")),
                    kind="attachment",
                )
            )
    data["evidence"] = ev

    cov = data.get("confidence", 0.5)
    try:
        data["confidence"] = float(cov)
    except (TypeError, ValueError):
        m = re.search(r"0?\.\d+|1(?:\.0+)?", str(cov))
        data["confidence"] = float(m.group(0)) if m else 0.5
    return data


def _methodology(
    mode: str, model: str, fallback: bool, n_files: int
) -> Dict[str, Any]:
    return {
        "personas": ["Scout", "Strategist", "Skeptic", "Forecaster"],
        "pipeline": (
            "ingest question + attachments → multi-persona analysis → "
            "synthesize prediction → governance audit"
        ),
        "mode": mode,
        "model": model or ("heuristic-mock" if mode == "mock" else "unknown"),
        "fallback_used": fallback,
        "attachments_count": n_files,
        "limitations": (
            "Not a certified forecast or professional advice. "
            "Quality depends on attachment completeness and mode (mock vs LLM). "
            "Always verify critical decisions with domain experts."
        ),
    }


def _collect_charts(attachments: Sequence[Attachment]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for a in attachments:
        for c in getattr(a, "charts", None) or []:
            if hasattr(c, "to_dict"):
                out.append(c.to_dict())
            elif isinstance(c, dict):
                out.append(c)
    return out


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

        self.requested_mode = mode if mode in ("mock", "llm") else "mock"
        self.mode = self.requested_mode
        self.llm_model = llm_model or "unsloth/Qwen3.6-35B-A3B-NVFP4"
        self.llm_base_url = llm_base_url or "http://spark-56bc:8888/v1"
        self.fallback_used = False

        self.identities = IdentityRegistry()
        self.audit = AuditLog(path=audit_path)
        self.permissions = PermissionEngine(
            identities=self.identities, audit=self.audit, open_mode=False
        )
        self.agent = self.identities.register(agent_name, agent_id="swarm-app-user")
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
                model=self.llm_model,
                base_url=self.llm_base_url,
                api_key=llm_api_key or "not-needed",
                timeout=120.0,
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

        raw: Dict[str, Any]
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
            if self.requested_mode == "llm":
                raw = MockPredictiveBackend().analyze(q, attachments)
                self.mode = "mock"
                self.fallback_used = True
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

        prediction = str(raw.get("prediction", ""))
        headline = str(raw.get("prediction_headline") or "").strip()
        detail = str(raw.get("prediction_detail") or "").strip()
        if not headline or not detail:
            h, d = split_prediction(prediction, q)
            headline = headline or h
            detail = detail or d

        data_insights = list(raw.get("data_insights") or [])
        evidence_raw = raw.get("evidence") or []
        if evidence_raw and isinstance(evidence_raw[0], EvidenceItem):
            evidence = list(evidence_raw)
        elif evidence_raw and isinstance(evidence_raw[0], dict):
            evidence = [
                EvidenceItem(
                    source=str(e.get("source", "unknown")),
                    excerpt=str(e.get("excerpt", ""))[:400],
                    claim=str(e.get("claim", "")),
                    kind=str(e.get("kind", "attachment")),
                )
                for e in evidence_raw
                if isinstance(e, dict)
            ]
        else:
            evidence = build_evidence(q, attachments, data_insights)

        model_used = (
            "heuristic-mock"
            if self.mode == "mock"
            else self.llm_model
        )

        report = PredictiveReport(
            run_id=uuid.uuid4().hex[:12],
            question=q,
            created_at=datetime.now(timezone.utc).isoformat(),
            mode=self.mode,
            executive_summary=str(raw.get("executive_summary", "")),
            prediction=prediction or detail,
            prediction_headline=headline,
            prediction_detail=detail,
            confidence=float(raw.get("confidence") or 0.5),
            time_horizon=str(raw.get("time_horizon", "")),
            key_drivers=list(raw.get("key_drivers") or []),
            scenarios=normalize_scenarios(raw.get("scenarios") or []),
            risks=list(raw.get("risks") or []),
            data_insights=data_insights,
            recommended_actions=list(raw.get("recommended_actions") or []),
            persona_views=list(personas),
            evidence=evidence,
            attachments_used=[a.filename for a in attachments],
            methodology=_methodology(
                self.mode, model_used, self.fallback_used, len(attachments)
            ),
            charts=_collect_charts(attachments),
            model_used=model_used,
            fallback_used=self.fallback_used,
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
                "fallback_used": report.fallback_used,
            },
        )
        report.audit_events = len(self.audit)
        report.chain_valid = self.audit.verify_chain()
        return report
