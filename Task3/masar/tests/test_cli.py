import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from masar.tests.helpers import ROOT, base_workflow, chain, lesson, write_json


def masar(*args):
    return subprocess.run([sys.executable, "-m", "masar", *map(str, args)], cwd=ROOT,
                          capture_output=True, encoding="utf-8")


class CliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.store = self.tmp / "output" / "python_drafts.json"

    def tearDown(self):
        self._tmp.cleanup()

    def test_lint_ok(self):
        r = masar("--lint")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("workflow ok: dorosak-content-intake", r.stdout)

    def test_lint_refuses_code(self):
        wf = chain("validate_lesson", "exec_python")
        wf["nodes"][0]["code"] = "print(1)"
        r = masar("--lint", "--workflow", write_json(self.tmp / "evil.json", wf))
        self.assertEqual(r.returncode, 1)
        self.assertIn("workflow rejected", r.stderr)
        self.assertIn("not code", r.stderr)
        self.assertIn("exec_python", r.stderr)

    def test_bad_workflow_stops_a_run(self):
        r = masar("--workflow", write_json(self.tmp / "evil.json", {"id": "x"}),
                  "--approved-by", "Trainer", "--store", self.store)
        self.assertEqual(r.returncode, 1)
        self.assertFalse(self.store.parent.exists())

    def test_graph(self):
        r = masar("--graph")
        self.assertEqual(r.returncode, 0)
        self.assertTrue(r.stdout.startswith("flowchart LR"))

    def test_brief_commands(self):
        steps = [(["--dry-run", "--approved-by", "Trainer"], "dry_run_preview", "dry-run"),
                 ([], "review_pending", "review"),
                 (["--approved-by", "Trainer"], "draft_saved", "approved"),
                 (["--approved-by", "Trainer"], "skipped_duplicate", "approved")]
        for args, status, mode in steps:
            with self.subTest(args=args):
                r = masar(*args, "--store", self.store)
                self.assertEqual(r.returncode, 0, r.stderr)
                report = json.loads(r.stdout)
                self.assertEqual(report["mode"], mode)
                self.assertEqual(report["summary"], {status: 4})
                self.assertNotIn("trace", report["items"][0])
                self.assertEqual(self.store.exists(), status in ("draft_saved", "skipped_duplicate"))

    def test_trace_flag(self):
        r = masar("--dry-run", "--approved-by", "Trainer", "--trace", "--store", self.store)
        self.assertEqual(len(json.loads(r.stdout)["items"][0]["trace"]), 7)

    def test_dry_run_refuses_html_in_output(self):
        html = self.store.parent / "report.html"
        r = masar("--dry-run", "--approved-by", "Trainer", "--store", self.store, "--report-html", html)
        self.assertEqual(r.returncode, 2)
        self.assertIn("dry run never writes in the output folder", r.stderr)
        self.assertFalse(self.store.parent.exists())

    def test_html_report(self):
        html = self.tmp / "report.html"
        r = masar("--approved-by", "Trainer", "--store", self.store, "--report-html", html)
        self.assertEqual(r.returncode, 0, r.stderr)
        text = html.read_text(encoding="utf-8")
        self.assertIn("Masar run report", text)
        self.assertIn("Drafts only. Nothing here is published.", text)
        self.assertIn("DOR-CAT-004", text)

    def test_arabic_output_prints(self):
        wf = base_workflow()
        wf["allowed_languages"] = ["ar"]
        lessons = [lesson(title="التحيات", language="ar", body="مرحبا كيف حالك")]
        r = masar("--workflow", write_json(self.tmp / "wf.json", wf),
                  "--input", write_json(self.tmp / "in.json", lessons),
                  "--store", self.store, "--approved-by", "Trainer")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["items"][0]["status"], "draft_saved")

    def test_input_with_bom(self):
        path = self.tmp / "bom.json"
        path.write_text(json.dumps([lesson()]), encoding="utf-8-sig")
        r = masar("--input", path, "--store", self.store)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_input_not_a_list(self):
        r = masar("--input", write_json(self.tmp / "in.json", lesson()), "--store", self.store)
        self.assertEqual(r.returncode, 2)
        self.assertIn("Input must be a JSON array", r.stderr)


class CommandTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.store = self.tmp / "output" / "python_drafts.json"

    def tearDown(self):
        self._tmp.cleanup()

    def test_review_then_resume(self):
        run_id = json.loads(masar("--store", self.store).stdout)["run_id"]
        r = masar("runs", "--store", self.store)
        self.assertIn(run_id, r.stdout)
        self.assertEqual(r.stdout.count("waiting:"), 4)

        r = masar("resume", "--run", run_id, "--store", self.store)
        self.assertEqual(r.returncode, 2)
        self.assertIn("resume refused: a reviewer name is needed", r.stderr)

        r = masar("resume", "--run", run_id, "--reject", "--reviewed-by", "Mona", "--item", "DOR-CAT-004",
                  "--store", self.store)
        self.assertIn("a reason is needed", r.stderr)
        r = masar("resume", "--run", run_id, "--reject", "--reviewed-by", "Mona", "--reason", "too long",
                  "--item", "DOR-CAT-004", "--store", self.store)
        self.assertEqual(json.loads(r.stdout)["items"], [{"source_id": "DOR-CAT-004", "status": "rejected"}])

        r = masar("resume", "--run", run_id, "--approved-by", "Mona", "--store", self.store)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(json.loads(r.stdout)["items"]), 3)
        self.assertEqual(len(json.loads(self.store.read_text(encoding="utf-8"))), 3)

        r = masar("verify-audit", "--store", self.store)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "audit chain ok: 8 lines")

    def test_verify_audit_broken(self):
        masar("--approved-by", "Trainer", "--store", self.store)
        audit = self.store.parent / "audit.jsonl"
        audit.write_text(audit.read_text(encoding="utf-8").replace("Trainer", "Boss", 1), encoding="utf-8")
        r = masar("verify-audit", "--audit", audit)
        self.assertEqual(r.returncode, 1)
        self.assertIn("audit chain BROKEN at line 1 of 4", r.stderr)

    def test_verify_audit_cut_at_the_end(self):
        masar("--approved-by", "Trainer", "--store", self.store)
        audit = self.store.parent / "audit.jsonl"
        rows = audit.read_text(encoding="utf-8").splitlines()
        audit.write_text("\n".join(rows[:-2]) + "\n", encoding="utf-8")
        r = masar("verify-audit", "--store", self.store)
        self.assertEqual(r.returncode, 1)
        self.assertIn("audit chain BROKEN after line 2: the file ends at line 2, but run", r.stderr)

    def test_verify_audit_no_file(self):
        r = masar("verify-audit", "--audit", self.tmp / "none.jsonl")
        self.assertEqual(r.stdout.strip(), "audit chain ok: 0 lines (no audit file yet)")

    def test_question_bank_default_store_name(self):
        from masar.cli import default_store
        self.assertEqual(default_store("dorosak-content-intake").name, "python_drafts.json")
        self.assertEqual(default_store("question-bank").name, "python_question-bank_drafts.json")
        self.assertEqual(default_store("a/../b").name, "python_a____b_drafts.json")

    def test_question_bank_cli(self):
        r = masar("--workflow", ROOT / "masar" / "workflows" / "question_bank.json",
                  "--input", ROOT / "masar" / "samples" / "questions.json",
                  "--dry-run", "--approved-by", "Trainer", "--store", self.store)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["summary"],
                         {"dry_run_preview": 2, "failed_validation": 6, "possible_duplicate": 1,
                          "skipped_duplicate": 1})


class StarterStillWorks(unittest.TestCase):
    def test_python_starter_tests(self):
        r = subprocess.run([sys.executable, "-m", "unittest"], cwd=ROOT / "starter" / "python",
                           capture_output=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_node_starter_tests(self):
        r = subprocess.run(["node", "--test"], cwd=ROOT / "starter" / "node",
                           capture_output=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
