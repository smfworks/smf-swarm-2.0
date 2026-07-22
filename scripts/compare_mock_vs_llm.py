#!/usr/bin/env python3
"""One-shot mock vs LLM comparison with compact prompt for reasoning models."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

import httpx


def normalize_base_url(base_url: str) -> str:
    """Reject URL userinfo so endpoint credentials cannot leak into artifacts."""

    parsed = urlsplit(base_url)
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("SMF_SWARM_EVAL_BASE_URL must not include credentials")
    return base_url.rstrip("/")


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from smf_swarm.capability.diagnostic import (  # noqa: E402
    CapabilityGap,
    MockCapabilityBackend,
    default_format_trajectory,
)

FIXTURE = ROOT / "fixtures" / "skillopt_edit_planning_trajectories.json"
OUT = ROOT / "data" / "mock_vs_llm_comparison.json"
RAW = ROOT / "data" / "llm_raw_response.txt"
BASE_URL = normalize_base_url(
    os.environ.get("SMF_SWARM_EVAL_BASE_URL", "http://spark-56bc:8888/v1")
)
MODEL = os.environ.get("SMF_SWARM_EVAL_MODEL", "").strip()


def resolve_model(client: httpx.Client, base_url: str, configured_model: str) -> str:
    """Use an explicit model or discover the endpoint's sole served model."""

    if configured_model:
        return configured_model
    response = client.get(f"{base_url.rstrip('/')}/models")
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise RuntimeError("model endpoint returned an invalid response")
    models: list[str] = []
    for item in payload["data"]:
        if not isinstance(item, dict):
            raise RuntimeError("model endpoint returned an invalid response")
        model_id = item.get("id")
        if not isinstance(model_id, str) or not model_id.strip():
            raise RuntimeError("model endpoint returned an invalid response")
        models.append(model_id.strip())
    if len(models) != 1:
        raise RuntimeError(
            "expected exactly one served model; set SMF_SWARM_EVAL_MODEL explicitly"
        )
    return models[0]


def parse_gaps(text: str, n: int = 6) -> list[CapabilityGap]:
    text = re.sub(r"<think>[\s\S]*?</think>", "", text or "", flags=re.I)
    gaps: list[CapabilityGap] = []
    for i, ch in enumerate(text):
        if ch != "[":
            continue
        try:
            data, _ = json.JSONDecoder().raw_decode(text[i:])
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("name"):
                    try:
                        cov = float(item.get("failure_coverage") or 0)
                    except (TypeError, ValueError):
                        cov = 0.0
                    gaps.append(
                        CapabilityGap(
                            name=str(item["name"]),
                            description=str(item.get("description", "")),
                            failure_coverage=cov,
                            evidence=[str(x) for x in (item.get("evidence") or [])][:3],
                            suggested_criterion=str(item.get("suggested_criterion", "")),
                        )
                    )
            if gaps:
                gaps.sort(key=lambda g: g.failure_coverage, reverse=True)
                return gaps[:n]
    for m in re.finditer(r"\{[^{}]+\}", text):
        try:
            item = json.loads(m.group(0))
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict) and item.get("name"):
            try:
                cov = float(item.get("failure_coverage") or 0)
            except (TypeError, ValueError):
                cov = 0.0
            gaps.append(
                CapabilityGap(
                    name=str(item["name"]),
                    description=str(item.get("description", "")),
                    failure_coverage=cov,
                    evidence=[str(x) for x in (item.get("evidence") or [])][:3],
                    suggested_criterion=str(item.get("suggested_criterion", "")),
                )
            )
    gaps.sort(key=lambda g: g.failure_coverage, reverse=True)
    return gaps[:n]


def themes(gaps: list[CapabilityGap]) -> list[str]:
    blob = " ".join(g.name + " " + g.description for g in gaps).lower()
    keys = {
        "priorit": "prioritization",
        "execut": "executable_plan",
        "risk": "risk",
        "evidence": "evidence",
        "depend": "dependencies",
        "order": "ordering",
        "specif": "specificity",
        "triage": "triage",
    }
    return sorted({v for k, v in keys.items() if k in blob})


def row(g: CapabilityGap) -> dict:
    return {
        "name": g.name,
        "failure_coverage": g.failure_coverage,
        "suggested_criterion": g.suggested_criterion,
        "description": (g.description or "")[:200],
    }


def main() -> int:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    successful, failed = data["successful"], data["failed"]
    domain = data.get("domain", "article_editing")

    mock_gaps = MockCapabilityBackend().analyze(successful, failed, domain, 8)

    succ = [default_format_trajectory(t)[:280] for t in successful[:2]]
    fail = [default_format_trajectory(t)[:280] for t in failed[:3]]
    prompt = (
        f"Domain: {domain}\n"
        f"SUCCESS: {succ}\n"
        f"FAILED: {fail}\n"
        "Return JSON array of exactly 3 objects with keys: "
        "name, description, failure_coverage, evidence, suggested_criterion. "
        "Keep each field short. JSON only."
    )
    with httpx.Client(timeout=180.0, trust_env=False) as client:
        model = resolve_model(client, BASE_URL, MODEL)
        body = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "Reply with a JSON array only. Exactly 3 concise items.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 2500,
        }

        print(f"Calling LLM on DGX Spark (model={model})...", flush=True)
        r = client.post(f"{BASE_URL}/chat/completions", json=body)
        r.raise_for_status()
        payload = r.json()
    msg = payload["choices"][0]["message"]
    content = msg.get("content") or ""
    reasoning = msg.get("reasoning") or ""
    raw = content.strip() if content and str(content).strip() else (reasoning or "")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    RAW.write_text(raw if raw else json.dumps(msg, default=str), encoding="utf-8")
    finish = payload["choices"][0].get("finish_reason")
    print(
        f"finish={finish} content_len={len(content or '')} reasoning_len={len(reasoning or '')}",
        flush=True,
    )

    llm_gaps = parse_gaps(raw)
    mock_t = set(themes(mock_gaps))
    llm_t = set(themes(llm_gaps))
    # avoid shell-sensitive & in shell wrappers; pure python set intersection
    overlap = sorted(mock_t.intersection(llm_t))

    if llm_gaps:
        rec = (
            "Use mock for offline CI/unit tests. "
            "Use LLM for production diagnosis when DGX/OpenAI-compatible endpoint is available. "
            "Prefer LLM suggested_criterion for SkillOpt criteria generation; "
            "mock is directionally aligned on core themes."
        )
    else:
        rec = (
            "LLM returned no parseable gaps this run — keep mock as CI default; "
            "inspect data/llm_raw_response.txt."
        )

    report = {
        "fixture": str(FIXTURE),
        "domain": domain,
        "model": model,
        "base_url": BASE_URL,
        "finish_reason": finish,
        "mock": {"n_gaps": len(mock_gaps), "gaps": [row(g) for g in mock_gaps]},
        "llm": {
            "error": None if llm_gaps else "no_gaps_parsed",
            "n_gaps": len(llm_gaps),
            "gaps": [row(g) for g in llm_gaps],
            "raw_preview": (raw or "")[:2000],
            "raw_path": str(RAW),
        },
        "theme_overlap": overlap,
        "mock_themes": sorted(mock_t),
        "llm_themes": sorted(llm_t),
        "recommendation": rec,
    }
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print("=== VERDICT ===")
    print(rec)
    return 0 if llm_gaps else 1


if __name__ == "__main__":
    raise SystemExit(main())
