# the 5 challenges from page 5 of the brief, run for real on the masar engine.
# each one runs in its own temp folder, so output/ is never touched.
#
#   python tools/challenges.py
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from masar.engine.executor import run_workflow  # noqa: E402

LESSON = {"source_id": "LAB-001", "title": "Greetings", "category": "75 Daily Conversations",
          "level": "A1", "language": "en", "body": "Hello! My name is Sara. Nice to meet you."}


def _hashes(folder):
    if not folder.exists():
        return None
    return {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob("*")) if p.is_file()}


def _drafts(store):
    return json.loads(store.read_text(encoding="utf-8")) if store.exists() else []


def fault_injection(store):
    r = run_workflow([{**LESSON, "title": ""}], approved_by="Trainer", store=store)
    status = r["items"][0]["status"]
    return status == "failed_validation" and not store.exists(), \
        f"{status}, drafts file {'written' if store.exists() else 'not written'}"


def idempotency(store):
    first = run_workflow([LESSON], approved_by="Trainer", store=store)["items"][0]["status"]
    second = run_workflow([LESSON], approved_by="Trainer", store=store)["items"][0]["status"]
    saved = len(_drafts(store))
    return (first, second, saved) == ("draft_saved", "skipped_duplicate", 1), \
        f"run 1 {first}, run 2 {second}, {saved} draft saved"


def review_gate(store):
    status = run_workflow([LESSON], store=store)["items"][0]["status"]
    return status == "review_pending" and not store.exists(), \
        f"{status}, drafts file {'written' if store.exists() else 'not written'}"


def dry_run(store):
    run_workflow([{**LESSON, "source_id": "LAB-000", "title": "Already saved"}], approved_by="Trainer", store=store)
    before = _hashes(store.parent)
    status = run_workflow([LESSON], approved_by="Trainer", dry_run=True, store=store)["items"][0]["status"]
    same = _hashes(store.parent) == before
    return status == "dry_run_preview" and same, \
        f"{status}, output folder {'unchanged' if same else 'CHANGED'}"


def new_node(store):
    item = run_workflow([LESSON], approved_by="Trainer", store=store)["items"][0]
    drafts = _drafts(store)
    in_draft = drafts[0].get("word_count") if drafts else None
    return item.get("word_count") == 9 and in_draft == 9, \
        f"report word_count {item.get('word_count')}, draft word_count {in_draft}"


CHALLENGES = [
    (1, "Fault Injection", "make the title empty", "failed_validation and nothing saved", fault_injection),
    (2, "Idempotency", "run approved twice", "skipped_duplicate on the second run", idempotency),
    (3, "Review Gate", "remove --approved-by", "review_pending", review_gate),
    (4, "Dry Run", "use --dry-run with a reviewer name", "the output folder does not change", dry_run),
    (5, "New Node", "add word_count + a test", "the report and the draft have the value", new_node),
]


def run_challenges():
    results = []
    for number, name, what, expected, check in CHALLENGES:
        with tempfile.TemporaryDirectory() as tmp:
            try:
                passed, got = check(Path(tmp) / "output" / "python_drafts.json")
            except Exception as ex:  # a crash is a fail, not a stop
                passed, got = False, f"{type(ex).__name__}: {ex}"
        results.append({"number": number, "name": name, "what": what, "expected": expected,
                        "got": got, "passed": passed})
    return results


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    results = run_challenges()
    for r in results:
        print(f"{r['number']}  {r['name']:<16} {'PASS' if r['passed'] else 'FAIL'}  {r['got']}")
    passed = sum(r["passed"] for r in results)
    print(f"\n{passed} of {len(results)} challenges pass")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
