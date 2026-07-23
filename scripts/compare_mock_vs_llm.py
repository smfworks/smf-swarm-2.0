#!/usr/bin/env python3
"""One-shot mock vs LLM comparison with compact prompt for reasoning models."""
from __future__ import annotations

import json
import math
import os
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import httpx


MAX_MODEL_ID_LENGTH = 256
_REQUIRED_GAP_FIELDS = frozenset(
    {
        "name",
        "description",
        "failure_coverage",
        "evidence",
        "suggested_criterion",
    }
)


def _contains_control_characters(value: str) -> bool:
    """Detect terminal, line, separator, and Unicode formatting characters."""

    return any(
        unicodedata.category(char) in {"Cc", "Cf", "Zl", "Zp"} for char in value
    )


def normalize_base_url(base_url: str) -> str:
    """Return a canonical endpoint URL with no output-tainting metadata."""

    if _contains_control_characters(base_url):
        raise ValueError("SMF_SWARM_EVAL_BASE_URL must not include control characters")
    if base_url != base_url.strip():
        raise ValueError("SMF_SWARM_EVAL_BASE_URL must not include surrounding whitespace")
    parsed = urlsplit(base_url)
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("SMF_SWARM_EVAL_BASE_URL must not include credentials")
    if "?" in base_url or "#" in base_url:
        raise ValueError("SMF_SWARM_EVAL_BASE_URL must not include a query or fragment")
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError("SMF_SWARM_EVAL_BASE_URL must be an absolute HTTP(S) URL")
    try:
        parsed.port
    except ValueError:
        raise ValueError(
            "SMF_SWARM_EVAL_BASE_URL must be an absolute HTTP(S) URL"
        ) from None
    return urlunsplit(
        (parsed.scheme.lower(), parsed.netloc, parsed.path.rstrip("/"), "", "")
    )


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
MODEL = os.environ.get("SMF_SWARM_EVAL_MODEL", "")


def resolve_model(client: httpx.Client, base_url: str, configured_model: str) -> str:
    """Use a validated explicit model or discover the endpoint's sole model."""

    if _contains_control_characters(configured_model):
        raise ValueError("SMF_SWARM_EVAL_MODEL must not include control characters")
    configured_model = configured_model.strip()
    if configured_model:
        if len(configured_model) > MAX_MODEL_ID_LENGTH:
            raise ValueError(
                f"SMF_SWARM_EVAL_MODEL must be at most {MAX_MODEL_ID_LENGTH} characters"
            )
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
        if not isinstance(model_id, str):
            raise RuntimeError("model endpoint returned an invalid response")
        if _contains_control_characters(model_id):
            raise RuntimeError("model endpoint returned an invalid response")
        model_id = model_id.strip()
        if not model_id or len(model_id) > MAX_MODEL_ID_LENGTH:
            raise RuntimeError("model endpoint returned an invalid response")
        models.append(model_id)
    if len(models) != 1:
        raise RuntimeError(
            "expected exactly one served model; set SMF_SWARM_EVAL_MODEL explicitly"
        )
    return models[0]


def _is_valid_gap_item(item: object) -> bool:
    if not isinstance(item, dict) or set(item) != _REQUIRED_GAP_FIELDS:
        return False
    for field in ("name", "description", "suggested_criterion"):
        value = item.get(field)
        if not isinstance(value, str) or not value.strip():
            return False
    evidence = item.get("evidence")
    if not isinstance(evidence, list) or not all(
        isinstance(entry, str) for entry in evidence
    ):
        return False
    return True


def _strict_gap_response_is_valid(text: str) -> bool:
    """Require one complete JSON array of three structurally valid gap objects."""

    candidate = re.sub(r"<think>[\s\S]*?</think>", "", text or "", flags=re.I).strip()
    try:
        data = json.loads(candidate)
    except (json.JSONDecodeError, TypeError):
        return False
    if not isinstance(data, list) or len(data) != 3:
        return False
    for item in data:
        if not _is_valid_gap_item(item):
            return False
        coverage = item.get("failure_coverage")
        coverage_value = float(coverage) if isinstance(coverage, (int, float)) else 0.0
        if (
            isinstance(coverage, bool)
            or not isinstance(coverage, (int, float))
            or not math.isfinite(coverage_value)
            or not 0.0 <= coverage_value <= 1.0
        ):
            return False
    return True


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
                if _is_valid_gap_item(item):
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
        if _is_valid_gap_item(item):
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

        print(f"Calling LLM on DGX Spark (model={model!r})...", flush=True)
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
    gap_names = {gap.name.strip().casefold() for gap in llm_gaps}
    llm_result_valid = (
        _strict_gap_response_is_valid(raw)
        and len(llm_gaps) == 3
        and len(gap_names) == 3
    )
    mock_t = set(themes(mock_gaps))
    llm_t = set(themes(llm_gaps))
    # avoid shell-sensitive & in shell wrappers; pure python set intersection
    overlap = sorted(mock_t.intersection(llm_t))

    if llm_result_valid:
        rec = (
            "Use mock for offline CI/unit tests. "
            "Use LLM for production diagnosis when DGX/OpenAI-compatible endpoint is available. "
            "Prefer LLM suggested_criterion for SkillOpt criteria generation; "
            "mock is directionally aligned on core themes."
        )
    else:
        rec = (
            "LLM result must contain exactly three distinct valid gaps — keep mock as "
            "the CI default and inspect data/llm_raw_response.txt."
        )

    report = {
        "fixture": str(FIXTURE),
        "domain": domain,
        "model": model,
        "base_url": BASE_URL,
        "finish_reason": finish,
        "mock": {"n_gaps": len(mock_gaps), "gaps": [row(g) for g in mock_gaps]},
        "llm": {
            "error": (
                None
                if llm_result_valid
                else "expected_exactly_three_distinct_valid_gaps"
            ),
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
    return 0 if llm_result_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
