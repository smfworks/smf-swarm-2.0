"""FastAPI application for SMF Swarm predictive analysis UI (v0.3)."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from smf_swarm.analysis import (
    Attachment,
    PredictiveSwarmEngine,
    extract_text_from_bytes,
)
from smf_swarm.app.history import RunHistory

STATIC_DIR = Path(__file__).resolve().parent / "static"
MAX_FILES = 8
MAX_FILE_BYTES = 5 * 1024 * 1024
APP_VERSION = "0.3.0"


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
        }

    @app.get("/api/history")
    def list_history(limit: int = 20):
        return {"items": history.list(limit=min(limit, 50))}

    @app.get("/api/history/{run_id}")
    def get_history(run_id: str):
        rep = history.get(run_id)
        if not rep:
            raise HTTPException(404, "run not found")
        return rep

    @app.get("/api/history/{run_id}/export.md")
    def export_markdown(run_id: str):
        rep = history.get(run_id)
        if not rep:
            raise HTTPException(404, "run not found")
        # Rebuild markdown via engine report shape
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
                run_id=rep.get("run_id", run_id),
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
            md = report.to_markdown()
        except Exception:
            md = json_fallback_md(rep)
        return PlainTextResponse(md, media_type="text/markdown; charset=utf-8")

    @app.post("/api/analyze")
    async def analyze(
        question: str = Form(...),
        mode: str = Form("mock"),
        files: Optional[List[UploadFile]] = File(None),
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
            attachments.append(
                Attachment(
                    filename=uf.filename,
                    content_type=uf.content_type or "application/octet-stream",
                    text=text,
                    size_bytes=len(raw),
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

        payload = report.to_dict()
        payload["markdown"] = report.to_markdown()
        try:
            history.append(payload)
        except Exception:
            pass
        return payload

    return app


def json_fallback_md(rep: dict) -> str:
    return (
        f"# Report {rep.get('run_id')}\n\n"
        f"## Question\n{rep.get('question')}\n\n"
        f"## Prediction\n{rep.get('prediction')}\n\n"
        f"{rep.get('executive_summary', '')}\n"
    )


app = create_app()
