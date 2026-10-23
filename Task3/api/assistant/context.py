# everything Ask Masar can see. read functions only, and the engine only as a dry run.
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

from masar.engine.errors import ResumeError
from masar.engine.executor import ROOT, run_workflow
from masar.engine.runs import list_runs, load_run

ITEM_MAX_BYTES = 64 * 1024
LESSONS_WORKFLOW = ROOT / "masar" / "workflows" / "dorosak_lessons.json"
SAMPLES = ROOT / "masar" / "samples"


class ContextError(Exception):
    pass


@dataclass
class Context:
    workflow: dict | None = None  # the raw workflow json
    report: dict | None = None
    item: dict | None = None
    run_id: str | None = None  # None for the last dry run, which is never saved
    dry: bool = False


def from_run(runs_dir, run_id, source_id=None, index=None):
    try:
        record = load_run(runs_dir, run_id)
    except ResumeError as ex:
        raise ContextError(str(ex)) from None
    report = record["report"]
    return Context(workflow=record["workflow"], report=report, run_id=run_id,
                   item=pick_item(report["items"], source_id, index))


def from_dry_item(item, workflow):
    # sent by the web app from its memory. it is only data: checked for shape and size.
    if len(json.dumps(item, ensure_ascii=False).encode("utf-8")) > ITEM_MAX_BYTES:
        raise ContextError(f"the lesson is too big (max {ITEM_MAX_BYTES // 1024} KB)")
    if not (isinstance(item, dict) and isinstance(item.get("status"), str)
            and isinstance(item.get("trace"), list) and isinstance(item.get("steps"), list)):
        raise ContextError("the lesson must have status, steps and trace")
    return Context(workflow=workflow, item=item, dry=True)


def find_lesson(runs_dir, source_id):
    # no run picked, but the question names a lesson: look in the newest runs first
    for summary in reversed(list_runs(runs_dir)):
        ctx = from_run(runs_dir, summary["run_id"], source_id=source_id)
        if ctx.item and ctx.item.get("source_id") == source_id:
            return ctx
    return None


def pick_item(items, source_id=None, index=None):
    if index is not None and 0 <= index < len(items):
        return items[index]
    if source_id is not None:
        return next((i for i in items if i.get("source_id") == source_id), None)
    return None


def default_workflow():
    return json.loads(LESSONS_WORKFLOW.read_text(encoding="utf-8"))


def sample_lesson(workflow):
    name = "questions.json" if workflow.get("id") == "question-bank" else "lessons_good.json"
    return json.loads((SAMPLES / name).read_text(encoding="utf-8"))[0]


def what_if(workflow, lesson):
    # the real engine, as a dry run, with an empty temp store: output/ is never read or written
    with tempfile.TemporaryDirectory() as tmp:
        report = run_workflow([lesson], dry_run=True, approved_by="what-if",
                              store=Path(tmp) / "none.json", workflow=workflow)
    return report["items"][0]
