"""Numeric series extraction and sparkline SVG generation."""
from __future__ import annotations

import csv
import io
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple


@dataclass
class ChartSeries:
    name: str
    filename: str
    values: List[float]
    labels: List[str] = field(default_factory=list)
    sparkline_svg: str = ""
    stats: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _parse_float(cell: str) -> Optional[float]:
    s = str(cell).strip().replace(",", "").replace("%", "")
    if not s or s in {".", "-", "n/a", "NA", "null"}:
        return None
    # strip currency
    s = re.sub(r"^[$€£]", "", s)
    try:
        return float(s)
    except ValueError:
        return None


def extract_series_from_csv(
    filename: str,
    text: str,
    *,
    max_series: int = 4,
    max_points: int = 80,
) -> List[ChartSeries]:
    """Extract up to max_series numeric columns from CSV text."""
    try:
        rows = list(csv.reader(io.StringIO(text)))
    except Exception:
        return []
    if len(rows) < 3:
        return []
    header = [h.strip() or f"col_{i}" for i, h in enumerate(rows[0])]
    body = rows[1:]
    series_out: List[ChartSeries] = []

    # Prefer first column as labels if non-numeric
    label_vals = [_parse_float(r[0]) if r else None for r in body]
    labels_are_numeric = sum(1 for v in label_vals if v is not None) >= max(2, len(body) // 2)

    for col_i, name in enumerate(header):
        if col_i == 0 and not labels_are_numeric:
            continue
        values: List[float] = []
        labels: List[str] = []
        for r in body:
            if col_i >= len(r):
                continue
            v = _parse_float(r[col_i])
            if v is None:
                continue
            values.append(v)
            if not labels_are_numeric and r:
                labels.append(str(r[0])[:24])
            else:
                labels.append(str(len(values)))
        if len(values) < 3:
            continue
        # downsample if needed
        if len(values) > max_points:
            step = max(1, len(values) // max_points)
            values = values[::step][:max_points]
            labels = labels[::step][:max_points]
        stats = {
            "n": float(len(values)),
            "min": min(values),
            "max": max(values),
            "last": values[-1],
            "first": values[0],
            "delta": values[-1] - values[0],
            "delta_pct": (
                ((values[-1] - values[0]) / abs(values[0])) * 100.0
                if values[0] != 0
                else 0.0
            ),
        }
        chart = ChartSeries(
            name=name,
            filename=filename,
            values=values,
            labels=labels,
            stats=stats,
        )
        chart.sparkline_svg = sparkline_svg(values, title=f"{filename}:{name}")
        series_out.append(chart)
        if len(series_out) >= max_series:
            break
    return series_out


def sparkline_svg(
    values: Sequence[float],
    *,
    width: int = 280,
    height: int = 56,
    title: str = "",
    stroke: str = "#6ee7ff",
    fill: str = "rgba(110,231,255,0.12)",
) -> str:
    """Pure SVG sparkline (no JS deps)."""
    if not values:
        return ""
    vals = list(values)
    lo, hi = min(vals), max(vals)
    span = hi - lo if hi != lo else 1.0
    pad = 4
    n = len(vals)
    pts: List[Tuple[float, float]] = []
    for i, v in enumerate(vals):
        x = pad + (i / max(1, n - 1)) * (width - 2 * pad)
        y = height - pad - ((v - lo) / span) * (height - 2 * pad)
        pts.append((x, y))
    poly = " ".join(f"{x:.2f},{y:.2f}" for x, y in pts)
    area = (
        f"{pad:.2f},{height - pad:.2f} "
        + poly
        + f" {width - pad:.2f},{height - pad:.2f}"
    )
    last = pts[-1]
    title_esc = (
        title.replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="100%" height="{height}" role="img" aria-label="{title_esc}">'
        f"<title>{title_esc}</title>"
        f'<polygon points="{area}" fill="{fill}" />'
        f'<polyline points="{poly}" fill="none" stroke="{stroke}" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />'
        f'<circle cx="{last[0]:.2f}" cy="{last[1]:.2f}" r="3" fill="{stroke}" />'
        f"</svg>"
    )


def extract_series_from_attachment_bytes(
    filename: str, data: bytes, content_type: str = ""
) -> List[ChartSeries]:
    name = filename.lower()
    if name.endswith(".csv") or "csv" in (content_type or ""):
        text = data.decode("utf-8", errors="replace")
        return extract_series_from_csv(filename, text)
    return []
