"""smf-swarm CLI — serve UI or run headless analysis."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    host = args.host
    port = args.port
    print(f"SMF Swarm UI → http://{host}:{port}")
    print("  POST /api/analyze  |  GET /api/health")
    uvicorn.run(
        "smf_swarm.app.server:app",
        host=host,
        port=port,
        reload=args.reload,
        log_level="info",
    )
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    from smf_swarm.analysis import (
        Attachment,
        PredictiveSwarmEngine,
        extract_text_from_bytes,
    )
    from smf_swarm.analysis.series import extract_series_from_attachment_bytes

    question = args.question
    if args.question_file:
        question = Path(args.question_file).read_text(encoding="utf-8")
    if not question or not str(question).strip():
        print("error: provide --question or --question-file", file=sys.stderr)
        return 2

    attachments = []
    for p in args.data or []:
        path = Path(p)
        raw = path.read_bytes()
        text = extract_text_from_bytes(path.name, raw)
        charts = extract_series_from_attachment_bytes(path.name, raw)
        attachments.append(
            Attachment(
                filename=path.name,
                content_type="application/octet-stream",
                text=text,
                size_bytes=len(raw),
                charts=charts,
            )
        )

    engine = PredictiveSwarmEngine(
        mode=args.mode,
        audit_path=args.audit or None,
        llm_model=args.model,
        llm_base_url=args.base_url,
    )
    report = engine.run(question.strip(), attachments)
    out = report.to_dict()
    if args.output:
        Path(args.output).write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"wrote {args.output}")
    else:
        print(json.dumps(out, indent=2))
    return 0 if report.chain_valid else 1


def cmd_diagnose(args: argparse.Namespace) -> int:
    from smf_swarm.pipeline.phase1_run import main as diagnose_main

    argv = []
    if args.fixture:
        argv += ["--fixture", args.fixture]
    if args.domain:
        argv += ["--domain", args.domain]
    if args.audit:
        argv += ["--audit", args.audit]
    return diagnose_main(argv)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="smf-swarm",
        description="SMF Swarm — governance-first predictive analysis application",
    )
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("serve", help="Start web UI + API")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8787)
    s.add_argument("--reload", action="store_true")
    s.set_defaults(func=cmd_serve)

    a = sub.add_parser("analyze", help="Headless predictive analysis")
    a.add_argument("--question", "-q", default="")
    a.add_argument("--question-file", default="")
    a.add_argument("--data", "-d", action="append", default=[], help="Attachment path (repeatable)")
    a.add_argument("--mode", choices=["mock", "llm"], default="mock")
    a.add_argument("--model", default=None)
    a.add_argument("--base-url", default=None)
    a.add_argument("--audit", default="")
    a.add_argument("--output", "-o", default="")
    a.set_defaults(func=cmd_analyze)

    d = sub.add_parser("diagnose", help="Phase 1 capability diagnostic CLI")
    d.add_argument("--fixture", default="")
    d.add_argument("--domain", default="article_editing")
    d.add_argument("--audit", default="")
    d.set_defaults(func=cmd_diagnose)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
