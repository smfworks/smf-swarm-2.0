"""Local run history for SMF Swarm app (JSONL)."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


def default_history_path() -> Path:
    env = os.environ.get("SMF_SWARM_HISTORY")
    if env:
        return Path(env)
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "smf-swarm" / "history.jsonl"


class RunHistory:
    def __init__(self, path: Optional[str | Path] = None, max_entries: int = 50):
        self.path = Path(path) if path else default_history_path()
        self.max_entries = max_entries
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, report: Dict[str, Any]) -> None:
        # Store a compact summary + full report
        slim = {
            "run_id": report.get("run_id"),
            "created_at": report.get("created_at"),
            "question": report.get("question"),
            "mode": report.get("mode"),
            "confidence": report.get("confidence"),
            "prediction_headline": report.get("prediction_headline"),
            "attachments_used": report.get("attachments_used"),
            "report": report,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(slim, default=str) + "\n")
        self._trim()

    def _trim(self) -> None:
        if not self.path.exists():
            return
        lines = self.path.read_text(encoding="utf-8").splitlines()
        if len(lines) <= self.max_entries:
            return
        kept = lines[-self.max_entries :]
        self.path.write_text("\n".join(kept) + "\n", encoding="utf-8")

    def list(self, limit: int = 20) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        items: List[Dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        items.reverse()
        out = []
        for it in items[:limit]:
            out.append(
                {
                    "run_id": it.get("run_id"),
                    "created_at": it.get("created_at"),
                    "question": it.get("question"),
                    "mode": it.get("mode"),
                    "confidence": it.get("confidence"),
                    "prediction_headline": it.get("prediction_headline"),
                    "attachments_used": it.get("attachments_used") or [],
                }
            )
        return out

    def get(self, run_id: str) -> Optional[Dict[str, Any]]:
        if not self.path.exists():
            return None
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                it = json.loads(line)
            except json.JSONDecodeError:
                continue
            if it.get("run_id") == run_id:
                return it.get("report") or it
        return None
