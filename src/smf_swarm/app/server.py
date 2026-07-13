"""FastAPI application for SMF Swarm predictive analysis UI."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from smf_swarm.analysis import (
    Attachment,
    PredictiveSwarmEngine,
    extract_text_from_bytes,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
MAX_FILES = 8
MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB each


def create_app() -> FastAPI:
    app = FastAPI(
        title="SMF Swarm",
        description="Governance-first predictive analysis swarm",
        version="0.2.0",
    )

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
            "version": "0.2.0",
            "mode_default": os.environ.get("SMF_SWARM_MODE", "mock"),
        }

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

        return report.to_dict()

    return app


app = create_app()
