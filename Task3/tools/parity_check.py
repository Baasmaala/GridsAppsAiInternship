# runs the python and node masar engines on the same workflow and samples
# and checks they give the same status for every lesson.
# every run uses its own temp drafts file, so output/ is never touched.
#
#   python tools/parity_check.py
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "masar" / "workflows" / "dorosak_lessons.json"
QUESTION_WF = ROOT / "masar" / "workflows" / "question_bank.json"
GOOD = ROOT / "masar" / "samples" / "lessons_good.json"
BAD = ROOT / "masar" / "samples" / "lessons_bad.json"
SIMILAR = ROOT / "masar" / "samples" / "lessons_similar.json"
QUESTIONS = ROOT / "masar" / "samples" / "questions.json"
EN_AR = "en+ar"  # the lessons workflow with "allowed_languages": ["en", "ar"], made in a temp folder
OUTPUT = ROOT / "output"
ENGINES = {
    "python": [sys.executable, "-m", "masar"],
    "node": ["node", str(ROOT / "masar" / "node" / "cli.mjs")],
}
DRY = ["--dry-run", "--approved-by", "Trainer"]
APPROVED = ["--approved-by", "Trainer"]

# (name, workflow, input, seed the drafts file?, runs). runs in one case share one drafts file.
CASES = [
    ("1. good sample, dry run", WORKFLOW, GOOD, False, [DRY]),
    ("2. bad sample, dry run", WORKFLOW, BAD, False, [DRY]),
    ("3. good sample, dry run, 2 lessons already saved", WORKFLOW, GOOD, True, [DRY]),
    ("4. good sample, no reviewer", WORKFLOW, GOOD, False, [[]]),
    ("5. good sample, approved, then the same command again", WORKFLOW, GOOD, False, [APPROVED, APPROVED]),
    ("6. question bank, dry run", QUESTION_WF, QUESTIONS, False, [DRY]),
    ("7. similar titles (english and arabic), dry run", EN_AR, SIMILAR, False, [DRY]),
]


def seed_drafts():
    lessons = json.loads(GOOD.read_text(encoding="utf-8"))[:2]
    return [{**x, "status": "draft", "reviewed_by": "Seed"} for x in lessons]


def run_engine(name, workflow, input_path, store, args):
    cmd = ENGINES[name] + ["--workflow", str(workflow), "--input", str(input_path),
                           "--store", str(store), *args]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, encoding="utf-8")
    if r.returncode != 0:
        raise SystemExit(f"{name} engine failed (exit {r.returncode}):\n{r.stderr}")
    return json.loads(r.stdout)


def run_case(workflow, input_path, seed, runs):
    # returns {engine: [report per run]}
    reports = {}
    with tempfile.TemporaryDirectory() as tmp:
        if workflow == EN_AR:
            wf = json.loads(WORKFLOW.read_text(encoding="utf-8"))
            wf["allowed_languages"] = ["en", "ar"]
            workflow = Path(tmp) / "en_ar.json"
            workflow.write_text(json.dumps(wf), encoding="utf-8")
        for name in ENGINES:
            store = Path(tmp) / name / "drafts.json"
            if seed:
                store.parent.mkdir(parents=True)
                store.write_text(json.dumps(seed_drafts()), encoding="utf-8")
            reports[name] = [run_engine(name, workflow, input_path, store, args) for args in runs]
    return reports


def output_hashes():
    if not OUTPUT.exists():
        return None
    return {str(p.relative_to(OUTPUT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(OUTPUT.rglob("*")) if p.is_file()}


def compare(py, nd):
    # statuses only: not error text, timestamps or run ids
    rows = []
    for i in range(max(len(py["items"]), len(nd["items"]))):
        a = py["items"][i] if i < len(py["items"]) else None
        b = nd["items"][i] if i < len(nd["items"]) else None
        lesson = str((a or b)["source_id"])
        same = a is not None and b is not None and a["source_id"] == b["source_id"] \
            and a["status"] == b["status"]
        rows.append((lesson, a["status"] if a else "-", b["status"] if b else "-", same))
    return rows, py["summary"] == nd["summary"]


def print_table(title, rows, summary_ok):
    widths = [max(len(r[i]) for r in rows + [("lesson", "python", "node", True)]) for i in range(3)]
    print(f"\n{title}")
    print(f"  {'lesson':<{widths[0]}}  {'python':<{widths[1]}}  {'node':<{widths[2]}}  match")
    for lesson, a, b, same in rows:
        print(f"  {lesson:<{widths[0]}}  {a:<{widths[1]}}  {b:<{widths[2]}}  {'yes' if same else 'NO'}")
    if not summary_ok:
        print("  summary counts: NO")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if not shutil.which("node"):
        print("node is not installed, cannot run the parity check", file=sys.stderr)
        return 2

    before = output_hashes()
    total = matched = cases_ok = 0
    for title, workflow, input_path, seed, runs in CASES:
        reports = run_case(workflow, input_path, seed, runs)
        case_ok = True
        for i, (py, nd) in enumerate(zip(reports["python"], reports["node"]), 1):
            rows, summary_ok = compare(py, nd)
            label = f"{title} (run {i})" if len(runs) > 1 else title
            print_table(label, rows, summary_ok)
            total += len(rows)
            matched += sum(r[3] for r in rows)
            case_ok = case_ok and summary_ok and all(r[3] for r in rows)
        cases_ok += case_ok

    untouched = output_hashes() == before
    print(f"\noutput/ untouched: {'yes' if untouched else 'NO'}")
    if cases_ok == len(CASES) and matched == total and untouched:
        print(f"all {len(CASES)} cases match: {matched} of {total} lessons")
        return 0
    print(f"MISMATCH: {cases_ok} of {len(CASES)} cases match, {matched} of {total} lessons")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
