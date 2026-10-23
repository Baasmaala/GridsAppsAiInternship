import copy
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import registry
from .audit import append_audit
from .context import Run
from .errors import ResumeError, ValidationError
from .fingerprint import fingerprint, print_source
from .loader import Workflow, load_workflow, parse_workflow
from .retry import GaveUp, call_with_retry
from .runs import audit_path, load_run, runs_dir, save_run
from .storage import atomic_json_write, read_store

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORKFLOW = ROOT / "masar" / "workflows" / "dorosak_lessons.json"
PAUSED = ("review_pending", "possible_duplicate")


def run_workflow(lessons, *, approved_by="", dry_run=False, store,
                 workflow_path=DEFAULT_WORKFLOW, workflow=None, sleep=time.sleep):
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
    now = _now()
    run = _new_run(wf, saved, reviewer, dry_run, now, sleep)

    results = [_run_item(raw, wf.nodes, run) for raw in lessons]
    items = [item for item, _ in results]
    report = {
        "run_id": str(uuid.uuid4()),
        "workflow_id": wf.id,
        "workflow_version": wf.version,
        "generated_at": now,
        "mode": "dry-run" if dry_run else ("approved" if reviewer else "review"),
        "summary": _summary(items),
        "items": items,
    }

    # dry run: nothing below this line happens
    if not dry_run:
        if run.new_drafts and run.reviewer:
            atomic_json_write(store, saved + run.new_drafts)
        pending = {item["source_id"]: pause for item, pause in results if pause}
        head = append_audit(audit_path(store), [_event("run", report, item, reviewer, now) for item in items])
        save_run(runs_dir(store), {"run_id": report["run_id"], "created_at": now, "updated_at": now,
                                   "workflow": wf.raw, "report": report, "pending": pending,
                                   "decisions": [], "audit_head": head})
    return report


def resume_run(run_id, *, store, reviewer, decision="approve", reason="", items=None, sleep=time.sleep):
    reviewer = reviewer.strip() if isinstance(reviewer, str) else ""
    reason = reason.strip() if isinstance(reason, str) else ""
    if decision not in ("approve", "reject"):
        raise ResumeError("decision must be approve or reject")
    if not reviewer:
        raise ResumeError("a reviewer name is needed. no name, no decision")
    if decision == "reject" and not reason:
        raise ResumeError("a reason is needed to reject")

    store = Path(store)
    record = load_run(runs_dir(store), run_id)
    wf = parse_workflow(record["workflow"])  # lint again, the run file could be edited
    pending = record["pending"]
    targets = _targets(record, items, decision)

    now = _now()
    report = record["report"]
    by_id = {item["source_id"]: item for item in report["items"] if item["source_id"] in targets}
    done = []
    if decision == "reject":
        approval = next(n["id"] for n in wf.nodes if n["type"] == "manual_approval")
        for sid in targets:
            pending.pop(sid)
            item = by_id[sid]
            item["status"] = "rejected"
            item["trace"].append({"node": approval, "type": "manual_approval", "result": "stop",
                                  "status": "rejected", "note": f"rejected by {reviewer}: {reason}"})
            done.append(item)
    else:
        saved = read_store(store)
        run = _new_run(wf, saved, reviewer, False, now, sleep, explicit=set(items or []))
        ids = [n["id"] for n in wf.nodes]
        for sid in targets:
            start = ids.index(pending[sid]["resume_from"])
            walk = _walk(copy.deepcopy(pending[sid]["data"]), wf.nodes, run, start)
            _merge(by_id[sid], walk)
            if walk["pause"]:
                pending[sid] = walk["pause"]
            else:
                pending.pop(sid)
            done.append(by_id[sid])
        if run.new_drafts:
            atomic_json_write(store, saved + run.new_drafts)

    for item in done:
        entry = {"time": now, "source_id": item["source_id"], "decision": decision,
                 "reviewer": reviewer, "status": item["status"]}
        if reason:
            entry["reason"] = reason
        record["decisions"].append(entry)
    report["summary"] = _summary(report["items"])
    record["updated_at"] = now
    record["audit_head"] = append_audit(audit_path(store),
                                        [_event(decision, report, item, reviewer, now, reason) for item in done])
    save_run(runs_dir(store), record)
    return {"run_id": run_id, "decision": decision, "reviewer": reviewer,
            "items": [{"source_id": i["source_id"], "status": i["status"]} for i in done],
            "still_waiting": {sid: p["status"] for sid, p in pending.items()}}


def _targets(record, items, decision):
    pending = record["pending"]
    if items:
        for sid in items:
            if sid not in pending:
                past = [d for d in record["decisions"] if d["source_id"] == sid]
                if past:
                    raise ResumeError(f"{sid} was already decided: {past[-1]['status']} "
                                      f"by {past[-1]['reviewer']}")
                raise ResumeError(f"{sid} is not waiting in run {record['run_id']}")
        return list(dict.fromkeys(items))
    if decision == "reject":
        targets = list(pending)
    else:
        # a name for the whole run is not a decision about a possible duplicate
        targets = [sid for sid, p in pending.items() if p["status"] == "review_pending"]
    if not targets:
        hint = " (possible duplicates must be approved one by one with --item)" if pending else ""
        raise ResumeError(f"nothing waiting to {decision} in run {record['run_id']}{hint}")
    return targets


def _now():
    return datetime.now(timezone.utc).isoformat()


def _new_run(wf, saved, reviewer, dry_run, now, sleep, explicit=()):
    known_ids, known_prints = set(), {}
    for d in saved:
        if isinstance(d, dict) and isinstance(d.get("source_id"), str):
            known_ids.add(d["source_id"])
            # older drafts have no fingerprint yet, so make it from the stored text
            fp = d.get("title_fingerprint") or fingerprint(print_source(d))
            if fp:
                known_prints.setdefault(fp, d["source_id"])
    return Run(reviewer=reviewer, dry_run=dry_run, allowed_languages=wf.allowed_languages, now=now,
               known_ids=known_ids, known_prints=known_prints, explicit_items=set(explicit), sleep=sleep)


def _summary(items):
    statuses = [item["status"] for item in items]
    return {s: statuses.count(s) for s in sorted(set(statuses))}


def _event(event, report, item, reviewer, now, reason=""):
    # small on purpose: ids, status, who and why. no lesson text.
    e = {"time": now, "event": event, "run_id": report["run_id"], "workflow_id": report["workflow_id"],
         "source_id": item["source_id"], "status": item["status"]}
    if reviewer:
        e["reviewer"] = reviewer
    if reason:
        e["reason"] = reason
    if item.get("possible_duplicate_of"):
        e["duplicate_of"] = item["possible_duplicate_of"]
    return e


def _walk(data, nodes, run, start=0):
    status, error, pause = "running", None, None
    steps, trace = [], []
    checkpoint = None  # where a resume starts again: the duplicate check
    for index in range(start, len(nodes)):
        node = nodes[index]
        if node["type"] == "check_duplicate":
            checkpoint = (node["id"], copy.deepcopy(data))
        steps.append(node["id"])
        entry = {"node": node["id"], "type": node["type"], "input": copy.deepcopy(data)}
        attempts = []
        begin = time.perf_counter()
        try:
            step = call_with_retry(lambda: registry.NODES[node["type"]](data, run), run.sleep, attempts)
        except ValidationError as ex:
            status, error = "failed_validation", str(ex)
        except GaveUp as ex:
            status, error = "failed_error", str(ex)
        except Exception as ex:
            # a bug in a node, not bad input. this lesson stops, the others go on
            status, error = "failed_error", f"{type(ex).__name__}: {ex}"
        entry["ms"] = round((time.perf_counter() - begin) * 1000, 3)
        if attempts:
            entry["attempts"] = attempts
        if error is not None:
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
            if status in PAUSED:
                at, at_data = checkpoint or (node["id"], data)
                pause = {"status": status, "resume_from": at, "data": at_data}
            break
    if status == "running":
        status = "complete"
    return {"status": status, "error": error, "steps": steps, "trace": trace, "data": data, "pause": pause}


def _run_item(raw, nodes, run):
    walk = _walk(copy.deepcopy(raw), nodes, run)
    item = {"source_id": raw.get("source_id", "UNKNOWN") if isinstance(raw, dict) else "UNKNOWN",
            "status": walk["status"], "steps": walk["steps"]}
    _add_extras(item, walk)
    item["trace"] = walk["trace"]
    return item, walk["pause"]


def _add_extras(item, walk):
    data = walk["data"]
    if isinstance(data, dict) and "word_count" in data:
        item["word_count"] = data["word_count"]
    if isinstance(data, dict) and data.get("possible_duplicate_of"):
        item["possible_duplicate_of"] = data["possible_duplicate_of"]
    if walk["error"] is not None:
        item["error"] = walk["error"]


def _merge(item, walk):
    # a resumed lesson: same item, more steps
    trace = item.pop("trace")
    item.pop("possible_duplicate_of", None)
    item["status"] = walk["status"]
    item["steps"] = item["steps"] + walk["steps"]
    _add_extras(item, walk)
    item["trace"] = trace + walk["trace"]
