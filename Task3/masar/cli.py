import argparse
import json
import re
import sys
from pathlib import Path

from .engine.audit import verify_audit
from .engine.errors import ResumeError, StoreError, WorkflowError
from .engine.executor import DEFAULT_WORKFLOW, ROOT, resume_run, run_workflow
from .engine.html_report import render_html
from .engine.loader import load_workflow, read_json, to_mermaid
from .engine.runs import audit_path, list_runs, load_run, runs_dir

OUTPUT_DIR = ROOT / "output"
DEFAULT_INPUT = ROOT / "masar" / "samples" / "lessons_good.json"
LESSONS_ID = "dorosak-content-intake"


def default_store(workflow_id):
    # the lessons workflow keeps the brief's file name, other workflows get their own file
    if workflow_id == LESSONS_ID:
        return OUTPUT_DIR / "python_drafts.json"
    return OUTPUT_DIR / f"python_{re.sub(r'[^A-Za-z0-9_-]', '_', workflow_id)}_drafts.json"


def _inside(path, folder):
    return path.resolve().is_relative_to(folder.resolve())


def _fail(msg, code=2):
    print(msg, file=sys.stderr)
    return code


def _print_json(value):
    print(json.dumps(value, indent=2, ensure_ascii=False))


def run_parser():
    p = argparse.ArgumentParser(prog="masar",
                                description="Masar: Dorosak lesson intake, local sandbox only. "
                                            "Other commands: runs, resume, verify-audit")
    p.add_argument("--workflow", type=Path, default=DEFAULT_WORKFLOW)
    p.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    p.add_argument("--store", type=Path, help="drafts file (default depends on the workflow)")
    p.add_argument("--approved-by", default="", help="test reviewer name, not a real login")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--lint", action="store_true", help="only check the workflow file")
    p.add_argument("--graph", action="store_true", help="print the workflow as a Mermaid diagram")
    p.add_argument("--report-html", type=Path, metavar="FILE", help="also save a readable report")
    p.add_argument("--trace", action="store_true", help="show the per-node trace in the output")
    return p


def run_command(argv):
    args = run_parser().parse_args(argv)
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

    store = args.store or default_store(wf.id)
    if args.dry_run and args.report_html and (
            _inside(args.report_html, OUTPUT_DIR) or _inside(args.report_html, store.parent)):
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
                              store=store, workflow=wf)
    except StoreError as ex:
        return _fail(str(ex))

    if args.report_html:
        args.report_html.parent.mkdir(parents=True, exist_ok=True)
        args.report_html.write_text(render_html(report), encoding="utf-8")

    if not args.trace:
        report = {**report, "items": [{k: v for k, v in item.items() if k != "trace"}
                                      for item in report["items"]]}
    _print_json(report)
    return 0


def runs_command(argv):
    p = argparse.ArgumentParser(prog="masar runs", description="list runs and what is waiting")
    p.add_argument("--store", type=Path, help="drafts file, its folder holds runs/")
    args = p.parse_args(argv)
    folder = runs_dir(args.store) if args.store else OUTPUT_DIR / "runs"
    runs = list_runs(folder)
    if not runs:
        print("no runs yet")
    for r in runs:
        counts = ", ".join(f"{s} {n}" for s, n in r["summary"].items())
        print(f"{r['run_id']}  {r['created_at'][:19]}  {r['workflow_id']}  {r['mode']}  ({counts})")
        for sid, status in r["waiting"].items():
            print(f"    waiting: {sid}  {status}")
    return 0


def resume_command(argv):
    p = argparse.ArgumentParser(prog="masar resume",
                                description="approve or reject lessons that wait in a run")
    p.add_argument("--run", required=True, help="run id (see: python -m masar runs)")
    p.add_argument("--approved-by", default="", help="test reviewer name, not a real login")
    p.add_argument("--reject", action="store_true")
    p.add_argument("--reviewed-by", default="", help="who rejects (or use --approved-by)")
    p.add_argument("--reason", default="", help="needed for --reject")
    p.add_argument("--item", action="append", help="only this source_id (can repeat)")
    p.add_argument("--store", type=Path, help="drafts file (default: the one for the run's workflow)")
    args = p.parse_args(argv)
    try:
        if args.store:
            store = args.store
        else:
            store = default_store(load_run(OUTPUT_DIR / "runs", args.run)["workflow"]["id"])
        result = resume_run(args.run, store=store, reviewer=args.reviewed_by or args.approved_by,
                            decision="reject" if args.reject else "approve",
                            reason=args.reason, items=args.item)
    except ResumeError as ex:
        return _fail(f"resume refused: {ex}")
    except WorkflowError as ex:
        return _fail("the run's workflow is not valid any more:\n" +
                     "\n".join(f"  - {e}" for e in ex.errors), 1)
    _print_json(result)
    return 0


def verify_command(argv):
    p = argparse.ArgumentParser(prog="masar verify-audit", description="check the audit hash chain")
    p.add_argument("--store", type=Path, help="drafts file, its folder holds audit.jsonl")
    p.add_argument("--audit", type=Path, help="the audit file itself")
    args = p.parse_args(argv)
    path = args.audit or (audit_path(args.store) if args.store else OUTPUT_DIR / "audit.jsonl")
    result = verify_audit(path)  # also checks the end against runs/ next to it
    if result["ok"]:
        print(f"audit chain ok: {result['lines']} lines" + (f" ({result['note']})" if "note" in result else ""))
        return 0
    where = (f"after line {result['lines']}" if result["broken_line"] > result["lines"]
             else f"at line {result['broken_line']} of {result['lines']}")
    return _fail(f"audit chain BROKEN {where}: {result['reason']}", 1)


COMMANDS = {"runs": runs_command, "resume": resume_command, "verify-audit": verify_command}


def main(argv=None):
    # windows terminals are not always utf-8, and lessons can be arabic
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv and argv[0] in COMMANDS:
        return COMMANDS[argv[0]](argv[1:])
    return run_command(argv)
