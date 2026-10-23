import json
import re
from pathlib import Path

from .errors import ResumeError
from .storage import atomic_json_write

RUN_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def runs_dir(store):
    return Path(store).parent / "runs"


def audit_path(store):
    return Path(store).parent / "audit.jsonl"


def save_run(folder, record):
    atomic_json_write(Path(folder) / f"{record['run_id']}.json", record)


def load_run(folder, run_id):
    # the id is also a file name, so only a real uuid gets through
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise ResumeError(f"not a run id: {run_id!r}")
    path = Path(folder) / f"{run_id}.json"
    if not path.exists():
        raise ResumeError(f"run not found: {run_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def list_runs(folder):
    folder = Path(folder)
    out = []
    for path in folder.glob("*.json") if folder.exists() else []:
        record = json.loads(path.read_text(encoding="utf-8"))
        out.append({"run_id": record["run_id"], "created_at": record["created_at"],
                    "workflow_id": record["workflow"]["id"], "mode": record["report"]["mode"],
                    "summary": record["report"]["summary"],
                    "waiting": {sid: p["status"] for sid, p in record["pending"].items()}})
    return sorted(out, key=lambda r: r["created_at"])
