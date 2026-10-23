"""Educational n8n-inspired sequential workflow engine; NO Dorosak production access."""
from __future__ import annotations
import argparse
import json
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / "shared" / "workflow.json"
DATA_PATH = ROOT / "shared" / "lessons.json"
ALLOWED_LEVELS = {"A1", "A2", "B1", "B2", "C1", "C2"}


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def atomic_json_write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                     prefix=".tmp-", suffix=".json", delete=False) as f:
        temp = Path(f.name)
        json.dump(value, f, indent=2, ensure_ascii=False)
        f.write("\n")
    temp.replace(path)


def run_workflow(lessons: list[dict], *, approved_by: str = "", dry_run: bool = False,
                 store: Path, workflow_path: Path = WORKFLOW_PATH) -> dict:
    wf = json.loads(workflow_path.read_text(encoding="utf-8"))
    nodes = wf["nodes"]
    ids = [node["id"] for node in nodes]
    expected_edges = [[ids[i], ids[i + 1]] for i in range(len(ids) - 1)]
    if wf["edges"] != expected_edges:
        raise ValueError("PoC only accepts a sequential chain; arbitrary DAGs are not supported")
    supported = {"validate_lesson", "normalize_lesson", "check_duplicate",
                 "manual_approval", "save_draft", "log_result"}
    if any(node["type"] not in supported for node in nodes):
        raise ValueError("Workflow contains an unknown node type")
    if store.exists():
        saved = json.loads(store.read_text(encoding="utf-8"))
        if not isinstance(saved, list):
            raise ValueError("Content store must contain a JSON array")
    else:
        saved = []
    known = {item["source_id"] for item in saved}
    outcomes = []
    for raw in lessons:
        ctx = {"data": dict(raw), "steps": [], "status": "running"}
        try:
            for node in nodes:
                action = node["type"]
                ctx["steps"].append(node["id"])
                d = ctx["data"]
                if action == "validate_lesson":
                    required = ("source_id", "title", "category", "level", "language", "body")
                    if any(not isinstance(d.get(k), str) or not d[k].strip() for k in required):
                        raise ValueError("Missing/empty field: " + ", ".join(
                            k for k in required if not isinstance(d.get(k), str) or not d[k].strip()))
                    if d["level"].strip().upper() not in ALLOWED_LEVELS:
                        raise ValueError("Invalid CEFR level")
                    if d["language"].strip().lower() != "en":
                        raise ValueError("Demo only accepts English lessons")
                elif action == "normalize_lesson":
                    d = {k: d[k].strip() for k in required}
                    d["level"] = d["level"].upper()
                    d["language"] = d["language"].lower()
                    d["slug"] = slugify(d["title"])
                    d["status"] = "draft"
                    if not d["slug"]:
                        raise ValueError("Cannot generate slug")
                    ctx["data"] = d
                elif action == "check_duplicate":
                    if d["source_id"] in known:
                        ctx["status"] = "skipped_duplicate"
                        break
                elif action == "manual_approval":
                    if not approved_by.strip():
                        ctx["status"] = "review_pending"
                        break
                elif action == "save_draft":
                    if dry_run:
                        ctx["status"] = "dry_run_preview"
                    else:
                        d["reviewed_by"] = approved_by.strip()
                        saved.append(d)
                        known.add(d["source_id"])
                        ctx["status"] = "draft_saved"
                elif action == "log_result":
                    pass
            if ctx["status"] == "running":
                ctx["status"] = "complete"
        except (ValueError, KeyError, TypeError) as ex:
            ctx["status"] = "failed_validation"
            ctx["error"] = str(ex)
        outcomes.append({"source_id": raw.get("source_id", "UNKNOWN") if isinstance(raw, dict) else "UNKNOWN",
                         "status": ctx["status"], "steps": ctx["steps"],
                         **({"error": ctx["error"]} if "error" in ctx else {})})
    # Educational single-process demo only: no lock or concurrent writers.
    if not dry_run and approved_by.strip():
        atomic_json_write(store, saved)
    return {"run_id": str(uuid.uuid4()), "workflow_id": wf["id"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": "dry-run" if dry_run else ("approved" if approved_by else "review"),
            "summary": {s: sum(o["status"] == s for o in outcomes) for s in sorted(set(o["status"] for o in outcomes))},
            "items": outcomes}


def main() -> None:
    parser = argparse.ArgumentParser(description="Dorosak lesson intake lab, sandbox only")
    parser.add_argument("--input", type=Path, default=DATA_PATH)
    parser.add_argument("--store", type=Path, default=ROOT / "output" / "python_drafts.json")
    parser.add_argument("--approved-by", default="", help="Simulated reviewer name; not real authentication")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    input_records = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(input_records, list):
        parser.error("Input must be a JSON array")
    report = run_workflow(input_records, approved_by=args.approved_by, dry_run=args.dry_run,
                          store=args.store)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
