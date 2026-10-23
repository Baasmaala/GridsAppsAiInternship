import copy
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import registry
from .context import Run
from .errors import ValidationError
from .loader import Workflow, load_workflow, parse_workflow
from .storage import atomic_json_write, read_store

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORKFLOW = ROOT / "masar" / "workflows" / "dorosak_lessons.json"


def run_workflow(lessons, *, approved_by="", dry_run=False, store,
                 workflow_path=DEFAULT_WORKFLOW, workflow=None):
    if workflow is None:
        wf = load_workflow(workflow_path)
    elif isinstance(workflow, Workflow):
        wf = workflow
    else:
        wf = parse_workflow(workflow)
    if not isinstance(lessons, list):
        raise ValueError("Input must be a JSON array")

    store = Path(store)
    saved = read_store(store)
    # trim once here, so "   " counts as no reviewer everywhere
    reviewer = approved_by.strip() if isinstance(approved_by, str) else ""
    now = datetime.now(timezone.utc).isoformat()
    run = Run(reviewer=reviewer, dry_run=dry_run, allowed_languages=wf.allowed_languages, now=now,
              known_ids={d["source_id"] for d in saved
                         if isinstance(d, dict) and isinstance(d.get("source_id"), str)})

    items = [_run_item(raw, wf.nodes, run) for raw in lessons]

    if run.new_drafts and run.reviewer and not dry_run:
        atomic_json_write(store, saved + run.new_drafts)

    statuses = [item["status"] for item in items]
    return {
        "run_id": str(uuid.uuid4()),
        "workflow_id": wf.id,
        "workflow_version": wf.version,
        "generated_at": now,
        "mode": "dry-run" if dry_run else ("approved" if reviewer else "review"),
        "summary": {s: statuses.count(s) for s in sorted(set(statuses))},
        "items": items,
    }


def _run_item(raw, nodes, run):
    data = copy.deepcopy(raw)
    status, error = "running", None
    steps, trace = [], []
    for node in nodes:
        steps.append(node["id"])
        entry = {"node": node["id"], "type": node["type"], "input": copy.deepcopy(data)}
        start = time.perf_counter()
        try:
            step = registry.NODES[node["type"]](data, run)
        except ValidationError as ex:
            status, error = "failed_validation", str(ex)
        except Exception as ex:
            # a bug in a node, not bad input. this lesson stops, the others go on
            status, error = "failed_error", f"{type(ex).__name__}: {ex}"
        entry["ms"] = round((time.perf_counter() - start) * 1000, 3)
        if error:
            entry.update(result="error", status=status, error=error)
            trace.append(entry)
            break
        data = step.data
        entry["output"] = copy.deepcopy(data)
        entry["result"] = "stop" if step.stop else "ok"
        if step.status:
            status = entry["status"] = step.status
        if step.note:
            entry["note"] = step.note
        trace.append(entry)
        if step.stop:
            break
    if status == "running":
        status = "complete"

    item = {"source_id": raw.get("source_id", "UNKNOWN") if isinstance(raw, dict) else "UNKNOWN",
            "status": status, "steps": steps}
    if isinstance(data, dict) and "word_count" in data:
        item["word_count"] = data["word_count"]
    if error:
        item["error"] = error
    item["trace"] = trace
    return item
