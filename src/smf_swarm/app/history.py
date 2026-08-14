"""Local run history for SMF Swarm app (JSONL)."""
from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, TextIO


def default_history_path() -> Path:
    env = os.environ.get("SMF_SWARM_HISTORY")
    if env:
        return Path(env)
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "smf-swarm" / "history.jsonl"


@contextmanager
def _exclusive_file(path: Path) -> Iterator[TextIO]:
    """Open JSONL with an exclusive lock for the whole read-modify-write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        if os.name == "posix":
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield handle
        finally:
            if os.name == "posix":
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _read_lines(handle: TextIO) -> List[str]:
    handle.seek(0)
    return [line for line in handle.read().splitlines() if line.strip()]


def _rewrite(handle: TextIO, lines: List[str]) -> None:
    handle.seek(0)
    handle.truncate()
    if lines:
        handle.write("\n".join(lines) + "\n")
    handle.flush()
    os.fsync(handle.fileno())


class RunHistory:
    def __init__(self, path: Optional[str | Path] = None, max_entries: int = 50):
        self.path = Path(path) if path else default_history_path()
        self.max_entries = max_entries
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, report: Dict[str, Any]) -> None:
        slim = {
            "run_id": report.get("run_id"),
            "share_id": report.get("share_id"),
            "created_at": report.get("created_at"),
            "question": report.get("question"),
            "mode": report.get("mode"),
            "confidence": report.get("confidence"),
            "prediction_headline": report.get("prediction_headline"),
            "attachments_used": report.get("attachments_used"),
            "report": report,
        }
        with _exclusive_file(self.path) as handle:
            lines = _read_lines(handle)
            lines.append(json.dumps(slim, default=str))
            if len(lines) > self.max_entries:
                lines = lines[-self.max_entries :]
            _rewrite(handle, lines)

    def _trim(self) -> None:
        if not self.path.exists():
            return
        with _exclusive_file(self.path) as handle:
            lines = _read_lines(handle)
            if len(lines) <= self.max_entries:
                return
            _rewrite(handle, lines[-self.max_entries :])

    def list(self, limit: int = 20) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for it in self._iter_records():
            items.append(it)
        items.reverse()
        out = []
        for it in items[:limit]:
            out.append(
                {
                    "run_id": it.get("run_id"),
                    "share_id": it.get("share_id")
                    or (it.get("report") or {}).get("share_id"),
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
        for it in self._iter_records():
            if it.get("run_id") == run_id:
                return it.get("report") or it
        return None

    def get_by_share_id(self, share_id: str) -> Optional[Dict[str, Any]]:
        if not share_id:
            return None
        for it in self._iter_records():
            sid = it.get("share_id") or (it.get("report") or {}).get("share_id")
            if sid == share_id:
                return it.get("report") or it
        return None

    def _iter_records(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        items: List[Dict[str, Any]] = []
        with _exclusive_file(self.path) as handle:
            for line in _read_lines(handle):
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return items
