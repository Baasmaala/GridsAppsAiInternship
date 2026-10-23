import argparse
import json
import sys
from pathlib import Path

from .engine.errors import StoreError, WorkflowError
from .engine.executor import DEFAULT_WORKFLOW, ROOT, run_workflow
from .engine.html_report import render_html
from .engine.loader import load_workflow, read_json, to_mermaid

OUTPUT_DIR = ROOT / "output"
DEFAULT_INPUT = ROOT / "masar" / "samples" / "lessons_good.json"
DEFAULT_STORE = OUTPUT_DIR / "python_drafts.json"


def build_parser():
    p = argparse.ArgumentParser(prog="masar",
                                description="Masar: Dorosak lesson intake, local sandbox only")
    p.add_argument("--workflow", type=Path, default=DEFAULT_WORKFLOW)
    p.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    p.add_argument("--store", type=Path, default=DEFAULT_STORE)
    p.add_argument("--approved-by", default="", help="test reviewer name, not a real login")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--lint", action="store_true", help="only check the workflow file")
    p.add_argument("--graph", action="store_true", help="print the workflow as a Mermaid diagram")
    p.add_argument("--report-html", type=Path, metavar="FILE", help="also save a readable report")
    p.add_argument("--trace", action="store_true", help="show the per-node trace in the output")
    return p


def _inside(path, folder):
    return path.resolve().is_relative_to(folder.resolve())


def _fail(msg, code=2):
    print(msg, file=sys.stderr)
    return code


def main(argv=None):
    # windows terminals are not always utf-8, and lessons can be arabic
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)

    try:
        wf = load_workflow(args.workflow)
    except WorkflowError as ex:
        lines = [f"workflow rejected: {args.workflow}"] + [f"  - {e}" for e in ex.errors]
        return _fail("\n".join(lines), 1)
    if args.lint:
        print(f"workflow ok: {wf.id} ({len(wf.nodes)} nodes, one straight line)")
        return 0
    if args.graph:
        print(to_mermaid(wf))
        return 0

    if args.dry_run and args.report_html and (
            _inside(args.report_html, OUTPUT_DIR) or _inside(args.report_html, args.store.parent)):
        return _fail("dry run never writes in the output folder. "
                     "pick another path for --report-html")

    try:
        lessons = read_json(args.input)
    except (OSError, json.JSONDecodeError) as ex:
        return _fail(f"cannot read input {args.input}: {ex}")
    if not isinstance(lessons, list):
        return _fail("Input must be a JSON array")

    try:
        report = run_workflow(lessons, approved_by=args.approved_by, dry_run=args.dry_run,
                              store=args.store, workflow=wf)
    except StoreError as ex:
        return _fail(str(ex))

    if args.report_html:
        args.report_html.parent.mkdir(parents=True, exist_ok=True)
        args.report_html.write_text(render_html(report), encoding="utf-8")

    if not args.trace:
        report = {**report, "items": [{k: v for k, v in item.items() if k != "trace"}
                                      for item in report["items"]]}
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0
