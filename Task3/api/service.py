import json
import re
import shutil
import threading
from pathlib import Path

from masar.cli import default_store
from masar.engine.audit import verify_audit
from masar.engine.errors import ResumeError, WorkflowError
from masar.engine.executor import ROOT, resume_run, run_workflow
from masar.engine.lint import lint
from masar.engine.loader import parse_workflow, to_mermaid
from masar.engine.runs import list_runs, load_run
from masar.engine.storage import atomic_json_write, read_store
from tools.challenges import run_challenges

from .assistant import chat as assistant
from .assistant.context import ContextError

WORKFLOWS = ROOT / "masar" / "workflows"
SAMPLES = ROOT / "masar" / "samples"
NAME = re.compile(r"[a-z0-9_-]{1,40}")
UPLOAD_MAX_BYTES = 200 * 1024
UPLOAD_MAX_ITEMS = 500


class NotFound(Exception):
    pass


class BadInput(Exception):
    pass


class Service:
    # everything the api does. no file path ever comes from the request,
    # only names that are looked up in fixed folders.

    def __init__(self, output_dir):
        self.output = Path(output_dir)
        self.lock = threading.Lock()  # one write at a time

    @property
    def runs(self):
        return self.output / "runs"

    @property
    def uploads(self):
        return self.output / "uploads"

    @property
    def audit_file(self):
        return self.output / "audit.jsonl"

    # workflows

    def _workflow_file(self, key):
        path = WORKFLOWS / f"{key}.json"
        if not NAME.fullmatch(key) or not path.exists():
            raise NotFound(f"no workflow called {key!r}")
        return path

    def _raw_workflow(self, key):
        try:
            return json.loads(self._workflow_file(key).read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as ex:
            raise WorkflowError([f"workflow file is not valid JSON: {ex}"]) from None

    def list_workflows(self):
        out = []
        for path in sorted(WORKFLOWS.glob("*.json")):
            raw = self._raw_workflow(path.stem)
            errors = lint(raw)
            out.append({"key": path.stem, "id": raw.get("id") if isinstance(raw, dict) else None,
                        "ok": not errors, "errors": errors})
        return out

    def get_workflow(self, key):
        raw = self._raw_workflow(key)
        errors = lint(raw)
        result = {"key": key, "ok": not errors, "errors": errors, "raw": raw}
        if not errors:
            wf = parse_workflow(raw)
            result.update(id=wf.id, version=wf.version, allowed_languages=wf.allowed_languages,
                          nodes=wf.nodes, edges=raw["edges"], mermaid=to_mermaid(wf))
        return result

    # samples

    def list_samples(self):
        out = [{"key": p.stem, "source": "built-in", "items": len(json.loads(p.read_text(encoding="utf-8")))}
               for p in sorted(SAMPLES.glob("*.json"))]
        if self.uploads.exists():
            out += [{"key": f"upload:{p.stem}", "source": "upload",
                     "items": len(json.loads(p.read_text(encoding="utf-8")))}
                    for p in sorted(self.uploads.glob("*.json"))]
        return out

    def read_sample(self, key):
        if key.startswith("upload:"):
            name, folder = key[len("upload:"):], self.uploads
        else:
            name, folder = key, SAMPLES
        path = folder / f"{name}.json"
        if not NAME.fullmatch(name) or not path.exists():
            raise NotFound(f"no sample called {key!r}")
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def save_upload(self, name, body):
        if not NAME.fullmatch(name or ""):
            raise BadInput("name may only use a-z, 0-9, _ and -, up to 40 characters")
        if len(body) > UPLOAD_MAX_BYTES:
            raise BadInput(f"file is too big ({len(body)} bytes, max {UPLOAD_MAX_BYTES})")
        try:
            data = json.loads(body.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as ex:
            raise BadInput(f"not valid JSON: {ex}") from None
        if not isinstance(data, list):
            raise BadInput("the file must be a JSON array of lessons")
        if len(data) > UPLOAD_MAX_ITEMS:
            raise BadInput(f"too many items ({len(data)}, max {UPLOAD_MAX_ITEMS})")
        bad = [str(i + 1) for i, x in enumerate(data) if not isinstance(x, dict)]
        if bad:
            raise BadInput(f"every item must be an object (not: item {', '.join(bad[:10])})")
        # the lessons themselves are checked by the workflow when it runs
        with self.lock:
            atomic_json_write(self.uploads / f"{name}.json", data)
        return {"key": f"upload:{name}", "items": len(data)}

    # runs

    def start_run(self, workflow_key, sample_key, dry_run, approved_by):
        if approved_by is not None and approved_by.strip() and not dry_run:
            raise BadInput("approved_by is only allowed with dry_run. "
                           "real saves happen in the review inbox, one lesson at a time")
        wf = parse_workflow(self._raw_workflow(workflow_key))
        lessons = self.read_sample(sample_key)
        with self.lock:
            return run_workflow(lessons, approved_by=approved_by or "", dry_run=dry_run,
                                store=default_store(wf.id, self.output), workflow=wf)

    def list_runs(self):
        return list_runs(self.runs)

    def get_run(self, run_id):
        try:
            record = load_run(self.runs, run_id)
        except ResumeError as ex:
            raise NotFound(str(ex)) from None
        return {k: record[k] for k in ("run_id", "created_at", "updated_at", "report", "decisions")} | {
            "workflow_id": record["workflow"]["id"],
            "waiting": {sid: p["status"] for sid, p in record["pending"].items()}}

    # review inbox

    def reviews(self):
        out = []
        for summary in list_runs(self.runs):
            record = load_run(self.runs, summary["run_id"])
            store = default_store(record["workflow"]["id"], self.output)
            items = {i["source_id"]: i for i in record["report"]["items"]}
            for sid, pending in record["pending"].items():
                item = items[sid]
                entry = {"run_id": record["run_id"], "workflow_id": record["workflow"]["id"],
                         "source_id": sid, "status": pending["status"], "created_at": record["created_at"],
                         "original": item["trace"][0]["input"], "normalized": pending["data"],
                         "word_count": item.get("word_count"),
                         "possible_duplicate_of": item.get("possible_duplicate_of")}
                if entry["possible_duplicate_of"]:
                    entry["old_draft"] = next((d for d in read_store(store)
                                               if d.get("source_id") == entry["possible_duplicate_of"]), None)
                out.append(entry)
        return out

    def decide(self, run_id, source_id, reviewer, decision, reason):
        try:
            record = load_run(self.runs, run_id)
        except ResumeError as ex:
            raise NotFound(str(ex)) from None
        store = default_store(record["workflow"]["id"], self.output)
        with self.lock:
            return resume_run(run_id, store=store, reviewer=reviewer, decision=decision,
                              reason=reason, items=[source_id])

    # drafts and audit

    def drafts(self):
        out = []
        for path in sorted(self.output.glob("python_*drafts.json")):
            for d in read_store(path):
                out.append({"file": path.name, "draft": d})
        return out

    def audit(self):
        if not self.audit_file.exists():
            return []
        return [json.loads(x) for x in self.audit_file.read_text(encoding="utf-8").splitlines() if x.strip()]

    def verify(self):
        return verify_audit(self.audit_file, self.runs)

    # ask masar. read only: no lock, no write function is passed in.

    def chat(self, question, lang, run_id=None, source_id=None, index=None, item=None, workflow=None):
        if not question.strip():
            raise BadInput("write a question")
        raw = self._raw_workflow(workflow or "dorosak_lessons") if item is not None else None
        try:
            return assistant.answer(question, lang, runs_dir=self.runs, run_id=run_id, source_id=source_id,
                                    index=index, item=item, workflow=raw)
        except ContextError as ex:
            raise BadInput(str(ex)) from None

    # lab and demo

    def challenges(self):
        return run_challenges()

    def reset(self, seed):
        # only ever deletes the output folder itself
        if self.output.name != "output":
            raise BadInput("refusing to reset: the output folder must be called 'output'")
        with self.lock:
            if self.output.exists():
                shutil.rmtree(self.output)
        result = {"cleared": True, "seeded": None}
        if seed:
            report = self.start_run("dorosak_lessons", "lessons_good", dry_run=False, approved_by=None)
            result["seeded"] = {"run_id": report["run_id"], "summary": report["summary"]}
        return result
