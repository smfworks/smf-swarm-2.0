"""FastAPI application for SMF Swarm predictive analysis UI (v0.4)."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from smf_swarm.analysis import (
    Attachment,
    PredictiveSwarmEngine,
    extract_text_from_bytes,
)
from smf_swarm.analysis.series import extract_series_from_attachment_bytes
from smf_swarm.app.auth import (
    auth_enabled,
    new_share_id,
    require_api_auth,
    sign_run_id,
    verify_run_signature,
)
from smf_swarm.app.history import RunHistory

STATIC_DIR = Path(__file__).resolve().parent / "static"
MAX_FILES = 8
MAX_FILE_BYTES = 5 * 1024 * 1024
APP_VERSION = "0.4.0"


def create_app() -> FastAPI:
    app = FastAPI(
        title="SMF Swarm",
        description="Governance-first predictive analysis swarm",
        version=APP_VERSION,
    )
    history = RunHistory()

    if STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    def index():
        index_path = STATIC_DIR / "index.html"
        if not index_path.is_file():
            raise HTTPException(500, "UI not packaged")
        return FileResponse(index_path)

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "service": "smf-swarm",
            "version": APP_VERSION,
            "mode_default": os.environ.get("SMF_SWARM_MODE", "mock"),
            "auth_required": auth_enabled(),
        }

    @app.get("/api/history")
    def list_history(limit: int = 20, _auth: None = Depends(require_api_auth)):
        return {"items": history.list(limit=min(limit, 50))}

    @app.get("/api/history/{run_id}")
    def get_history(run_id: str, _auth: None = Depends(require_api_auth)):
        rep = history.get(run_id)
        if not rep:
            raise HTTPException(404, "run not found")
        return rep

    @app.get("/api/history/{run_id}/export.md")
    def export_markdown(run_id: str, _auth: None = Depends(require_api_auth)):
        rep = history.get(run_id)
        if not rep:
            raise HTTPException(404, "run not found")
        return PlainTextResponse(
            _report_markdown(rep), media_type="text/markdown; charset=utf-8"
        )

    # Public shareable report (no API token)
    @app.get("/api/share/{share_id}")
    def api_share(share_id: str):
        rep = history.get_by_share_id(share_id)
        if not rep:
            raise HTTPException(404, "shared report not found")
        return rep

    @app.get("/share/{share_id}", response_class=HTMLResponse)
    def share_page(share_id: str):
        rep = history.get_by_share_id(share_id)
        if not rep:
            raise HTTPException(404, "shared report not found")
        return _share_html(rep)

    @app.get("/r/{run_id}", response_class=HTMLResponse)
    def signed_report_page(run_id: str, s: str = ""):
        if not verify_run_signature(run_id, s):
            raise HTTPException(403, "invalid or missing share signature")
        rep = history.get(run_id)
        if not rep:
            raise HTTPException(404, "run not found")
        return _share_html(rep)

    @app.post("/api/analyze")
    async def analyze(
        question: str = Form(...),
        mode: str = Form("mock"),
        files: Optional[List[UploadFile]] = File(None),
        _auth: None = Depends(require_api_auth),
    ):
        q = (question or "").strip()
        if not q:
            raise HTTPException(400, "question is required")
        if len(q) > 8000:
            raise HTTPException(400, "question too long")

        mode = (mode or "mock").lower().strip()
        if mode not in ("mock", "llm"):
            mode = "mock"

        attachments: List[Attachment] = []
        upload_list = files or []
        if len(upload_list) > MAX_FILES:
            raise HTTPException(400, f"max {MAX_FILES} files")

        for uf in upload_list:
            if not uf.filename:
                continue
            raw = await uf.read()
            if len(raw) > MAX_FILE_BYTES:
                raise HTTPException(400, f"{uf.filename}: file too large (max 5MB)")
            text = extract_text_from_bytes(
                uf.filename, raw, uf.content_type or ""
            )
            charts = extract_series_from_attachment_bytes(
                uf.filename, raw, uf.content_type or ""
            )
            attachments.append(
                Attachment(
                    filename=uf.filename,
                    content_type=uf.content_type or "application/octet-stream",
                    text=text,
                    size_bytes=len(raw),
                    charts=charts,
                )
            )

        audit_dir = Path(tempfile.gettempdir()) / "smf-swarm-audits"
        audit_dir.mkdir(parents=True, exist_ok=True)
        audit_path = audit_dir / "app-audit.jsonl"

        engine = PredictiveSwarmEngine(
            mode=mode,
            audit_path=audit_path,
            llm_model=os.environ.get("SMF_SWARM_LLM_MODEL"),
            llm_base_url=os.environ.get("SMF_SWARM_LLM_BASE_URL"),
            llm_api_key=os.environ.get("SMF_SWARM_LLM_API_KEY", ""),
        )
        try:
            report = engine.run(q, attachments)
        except Exception as e:
            raise HTTPException(500, f"analysis failed: {e}") from e

        share_id = new_share_id()
        report.share_id = share_id
        sig = sign_run_id(report.run_id)
        report.share_path = f"/share/{share_id}"
        payload = report.to_dict()
        payload["markdown"] = report.to_markdown()
        payload["share_url_path"] = report.share_path
        payload["signed_url_path"] = f"/r/{report.run_id}?s={sig}"
        try:
            history.append(payload)
        except Exception:
            pass
        return payload

    return app


def _report_markdown(rep: dict) -> str:
    from smf_swarm.analysis.engine import (
        EvidenceItem,
        PersonaView,
        PredictiveReport,
    )

    personas = [
        PersonaView(**p) if isinstance(p, dict) else p
        for p in (rep.get("persona_views") or [])
    ]
    evidence = [
        EvidenceItem(**e) if isinstance(e, dict) else e
        for e in (rep.get("evidence") or [])
    ]
    try:
        report = PredictiveReport(
            run_id=rep.get("run_id", ""),
            question=rep.get("question", ""),
            created_at=rep.get("created_at", ""),
            mode=rep.get("mode", ""),
            executive_summary=rep.get("executive_summary", ""),
            prediction=rep.get("prediction", ""),
            prediction_headline=rep.get("prediction_headline", ""),
            prediction_detail=rep.get("prediction_detail", ""),
            confidence=float(rep.get("confidence") or 0),
            time_horizon=rep.get("time_horizon", ""),
            key_drivers=list(rep.get("key_drivers") or []),
            scenarios=list(rep.get("scenarios") or []),
            risks=list(rep.get("risks") or []),
            data_insights=list(rep.get("data_insights") or []),
            recommended_actions=list(rep.get("recommended_actions") or []),
            persona_views=personas,
            evidence=evidence,
            attachments_used=list(rep.get("attachments_used") or []),
            methodology=dict(rep.get("methodology") or {}),
            charts=list(rep.get("charts") or []),
            share_id=rep.get("share_id", ""),
            share_path=rep.get("share_path", ""),
            model_used=rep.get("model_used", ""),
            fallback_used=bool(rep.get("fallback_used")),
            audit_events=int(rep.get("audit_events") or 0),
            chain_valid=bool(rep.get("chain_valid")),
            agent_id=rep.get("agent_id", ""),
            disclaimer=rep.get(
                "disclaimer",
                "Decision support only — not professional advice.",
            ),
        )
        return report.to_markdown()
    except Exception:
        return f"# Report {rep.get('run_id')}\n\n{rep.get('prediction', '')}\n"


def _share_html(rep: dict) -> str:
    headline = rep.get("prediction_headline") or rep.get("prediction") or "Report"
    conf = float(rep.get("confidence") or 0)
    summary = rep.get("executive_summary") or ""
    detail = rep.get("prediction_detail") or rep.get("prediction") or ""
    q = rep.get("question") or ""
    run_id = rep.get("run_id") or ""
    charts_html = ""
    for c in rep.get("charts") or []:
        svg = c.get("sparkline_svg") or ""
        name = c.get("name") or "series"
        fn = c.get("filename") or ""
        stats = c.get("stats") or {}
        charts_html += (
            f"<div class='chart'><div class='chart-title'>{_esc(fn)} · {_esc(name)} "
            f"(last={_esc(str(stats.get('last', '')))} Δ={_esc(str(stats.get('delta', '')))})</div>"
            f"{svg}</div>"
        )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>SMF Swarm Share · {_esc(headline)}</title>
<style>
body{{margin:0;font-family:system-ui,sans-serif;background:#0b0f17;color:#e8eef9;line-height:1.5}}
.wrap{{max-width:720px;margin:0 auto;padding:2rem 1.25rem}}
.card{{background:#121826;border:1px solid rgba(148,163,184,.14);border-radius:14px;padding:1.1rem 1.2rem;margin:1rem 0}}
h1{{font-size:1.4rem;margin:0 0 .5rem}}
.muted{{color:#94a3b8;font-size:.9rem}}
.pill{{display:inline-block;padding:.2rem .6rem;border-radius:999px;border:1px solid rgba(110,231,255,.35);color:#6ee7ff;font-size:.78rem}}
.chart{{margin:.75rem 0;padding:.75rem;border:1px solid rgba(148,163,184,.14);border-radius:12px;background:rgba(0,0,0,.2)}}
.chart-title{{font-size:.8rem;color:#94a3b8;margin-bottom:.35rem}}
a{{color:#6ee7ff}}
</style></head><body><div class="wrap">
<div class="muted">SMF Swarm · shared report · <span class="pill">{int(conf*100)}% confidence</span></div>
<h1>{_esc(str(headline))}</h1>
<p class="muted">run {_esc(run_id)}</p>
<div class="card"><strong>Question</strong><p>{_esc(q)}</p></div>
<div class="card"><strong>Prediction</strong><p>{_esc(detail)}</p></div>
<div class="card"><strong>Summary</strong><p>{_esc(summary)}</p></div>
{f"<div class='card'><strong>Charts</strong>{charts_html}</div>" if charts_html else ""}
<p class="muted">Decision support only — not professional advice. <a href="/">Open SMF Swarm</a></p>
</div></body></html>"""


def _esc(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


app = create_app()
