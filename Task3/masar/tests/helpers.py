import copy
import hashlib
import json
from pathlib import Path

from masar.engine.executor import DEFAULT_WORKFLOW, ROOT

LESSON = {"source_id": "L1", "title": "Greetings", "category": "Conversations",
          "level": "A1", "language": "en", "body": "Hello! My name is Sara."}


def lesson(**changes):
    return {**LESSON, **changes}


def base_workflow():
    return json.loads(DEFAULT_WORKFLOW.read_text(encoding="utf-8"))


def chain(*types, **extra):
    # build a straight-line workflow from node types, ids are n1, n2...
    nodes = [{"id": f"n{i}", "type": t} for i, t in enumerate(types, 1)]
    edges = [[f"n{i}", f"n{i + 1}"] for i in range(1, len(types))]
    return {"id": "test", "trigger": {"type": "manual"}, "nodes": nodes, "edges": edges, **extra}


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


def folder_hashes(folder):
    folder = Path(folder)
    if not folder.exists():
        return None
    return {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob("*")) if p.is_file()}


def without_times(report):
    # run_id, timestamps and ms change every run, the rest must not
    r = copy.deepcopy(report)
    r.pop("run_id")
    r.pop("generated_at")
    for item in r["items"]:
        for entry in item["trace"]:
            entry.pop("ms")
    return r


__all__ = ["ROOT", "LESSON", "lesson", "base_workflow", "chain", "write_json",
           "folder_hashes", "without_times"]
