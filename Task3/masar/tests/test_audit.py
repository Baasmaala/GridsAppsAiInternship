import json
import tempfile
import unittest
from pathlib import Path

from masar.engine.audit import verify_audit
from masar.engine.executor import resume_run, run_workflow
from masar.tests.helpers import ROOT

GOOD = json.loads((ROOT / "masar" / "samples" / "lessons_good.json").read_text(encoding="utf-8"))
BAD = json.loads((ROOT / "masar" / "samples" / "lessons_bad.json").read_text(encoding="utf-8"))
SMALL_KEYS = {"seq", "time", "event", "run_id", "workflow_id", "source_id", "status",
              "reviewer", "reason", "duplicate_of", "prev_hash", "hash"}


class AuditTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name) / "output"
        self.store = self.dir / "python_drafts.json"
        self.audit = self.dir / "audit.jsonl"

    def tearDown(self):
        self._tmp.cleanup()

    def lines(self):
        return [json.loads(x) for x in self.audit.read_text(encoding="utf-8").splitlines()]

    def edit_line(self, n, change):
        rows = self.audit.read_text(encoding="utf-8").splitlines()
        rows[n - 1] = change(rows[n - 1])
        self.audit.write_text("\n".join(rows) + "\n", encoding="utf-8")

    def test_one_line_per_lesson_every_status(self):
        run_workflow(GOOD + BAD, approved_by="Trainer", store=self.store)
        lines = self.lines()
        self.assertEqual(len(lines), 12)
        self.assertEqual([x["seq"] for x in lines], list(range(1, 13)))
        self.assertEqual(lines[4]["status"], "failed_validation")
        self.assertEqual(verify_audit(self.audit), {"ok": True, "lines": 12})

    def test_lines_are_small(self):
        run_workflow(GOOD, approved_by="Trainer", store=self.store)
        text = self.audit.read_text(encoding="utf-8")
        for line in self.lines():
            self.assertLessEqual(set(line), SMALL_KEYS)
        for lesson in GOOD:
            self.assertNotIn(lesson["body"].strip(), text)
            self.assertNotIn(lesson["title"].strip(), text)

    def test_resume_and_reject_are_logged(self):
        run_id = run_workflow(GOOD[:2], store=self.store)["run_id"]
        resume_run(run_id, store=self.store, reviewer="Mona", items=["DOR-CAT-001"])
        resume_run(run_id, store=self.store, reviewer="Mona", decision="reject", reason="not needed")
        events = [(x["event"], x["source_id"], x["status"], x.get("reason")) for x in self.lines()]
        self.assertEqual(events, [("run", "DOR-CAT-001", "review_pending", None),
                                  ("run", "DOR-CAT-002", "review_pending", None),
                                  ("approve", "DOR-CAT-001", "draft_saved", None),
                                  ("reject", "DOR-CAT-002", "rejected", "not needed")])
        self.assertTrue(verify_audit(self.audit)["ok"])

    def test_chain_continues_across_runs(self):
        run_workflow(GOOD, store=self.store)
        run_workflow(GOOD, approved_by="Trainer", store=self.store)
        lines = self.lines()
        self.assertEqual(lines[4]["prev_hash"], lines[3]["hash"])
        self.assertEqual(verify_audit(self.audit), {"ok": True, "lines": 8})

    def test_dry_run_writes_no_audit(self):
        run_workflow(GOOD, approved_by="Trainer", dry_run=True, store=self.store)
        self.assertFalse(self.audit.exists())
        self.assertEqual(verify_audit(self.audit)["lines"], 0)

    def test_edited_line_is_found(self):
        run_workflow(GOOD, approved_by="Trainer", store=self.store)
        self.edit_line(3, lambda s: s.replace('"draft_saved"', '"rejected"'))
        result = verify_audit(self.audit)
        self.assertFalse(result["ok"])
        self.assertEqual(result["broken_line"], 3)
        self.assertIn("this line was edited", result["reason"])

    def test_edited_reviewer_is_found(self):
        run_workflow(GOOD, approved_by="Trainer", store=self.store)
        self.edit_line(2, lambda s: s.replace('"Trainer"', '"Boss"'))
        self.assertEqual(verify_audit(self.audit)["broken_line"], 2)

    def test_removed_line_is_found(self):
        run_workflow(GOOD, approved_by="Trainer", store=self.store)
        rows = self.audit.read_text(encoding="utf-8").splitlines()
        del rows[1]
        self.audit.write_text("\n".join(rows) + "\n", encoding="utf-8")
        result = verify_audit(self.audit)
        self.assertEqual(result["broken_line"], 2)
        self.assertIn("removed, added or moved", result["reason"])

    def test_rehashed_line_still_breaks_the_next_one(self):
        # someone edits line 2 and fixes its own hash: line 3 no longer matches
        from masar.engine.audit import line_hash
        run_workflow(GOOD, approved_by="Trainer", store=self.store)
        rows = self.audit.read_text(encoding="utf-8").splitlines()
        entry = json.loads(rows[1])
        entry["status"] = "rejected"
        entry["hash"] = line_hash(entry["prev_hash"], {k: v for k, v in entry.items() if k != "hash"})
        rows[1] = json.dumps(entry)
        self.audit.write_text("\n".join(rows) + "\n", encoding="utf-8")
        self.assertEqual(verify_audit(self.audit)["broken_line"], 3)

    def test_cut_at_the_end_is_found(self):
        run_workflow(GOOD, approved_by="Trainer", store=self.store)
        rows = self.audit.read_text(encoding="utf-8").splitlines()
        self.audit.write_text("\n".join(rows[:-2]) + "\n", encoding="utf-8")
        result = verify_audit(self.audit)
        self.assertFalse(result["ok"])
        self.assertEqual((result["lines"], result["broken_line"]), (2, 3))
        self.assertIn("the file ends at line 2, but run", result["reason"])
        self.assertIn("saw 4 lines (lines were cut from the end)", result["reason"])

    def test_deleted_audit_file_is_found(self):
        run_workflow(GOOD, store=self.store)
        self.audit.unlink()
        result = verify_audit(self.audit)
        self.assertFalse(result["ok"])
        self.assertIn("no audit file, but run", result["reason"])

    def test_replaced_end_is_found(self):
        # cut the last line and write a new valid one in its place
        from masar.engine.audit import append_audit
        run_workflow(GOOD, approved_by="Trainer", store=self.store)
        rows = self.audit.read_text(encoding="utf-8").splitlines()
        self.audit.write_text("\n".join(rows[:-1]) + "\n", encoding="utf-8")
        append_audit(self.audit, [{"event": "run", "source_id": "FAKE", "status": "draft_saved"}])
        result = verify_audit(self.audit)
        self.assertEqual(result["broken_line"], 4)
        self.assertIn("the end was replaced", result["reason"])

    def test_run_file_keeps_the_head(self):
        run_id = run_workflow(GOOD[:2], store=self.store)["run_id"]
        head = json.loads((self.dir / "runs" / f"{run_id}.json").read_text(encoding="utf-8"))["audit_head"]
        self.assertEqual((head["lines"], head["hash"]), (2, self.lines()[-1]["hash"]))
        resume_run(run_id, store=self.store, reviewer="Mona")
        head = json.loads((self.dir / "runs" / f"{run_id}.json").read_text(encoding="utf-8"))["audit_head"]
        self.assertEqual((head["lines"], head["hash"]), (4, self.lines()[-1]["hash"]))

    def test_cut_is_missed_only_if_run_files_go_too(self):
        import shutil
        run_workflow(GOOD, approved_by="Trainer", store=self.store)
        rows = self.audit.read_text(encoding="utf-8").splitlines()
        self.audit.write_text("\n".join(rows[:-2]) + "\n", encoding="utf-8")
        shutil.rmtree(self.dir / "runs")
        self.assertTrue(verify_audit(self.audit)["ok"])

    def test_garbage_line_is_found(self):
        run_workflow(GOOD, approved_by="Trainer", store=self.store)
        self.edit_line(4, lambda s: s[:20])
        result = verify_audit(self.audit)
        self.assertEqual((result["broken_line"], result["reason"]), (4, "not valid JSON"))


if __name__ == "__main__":
    unittest.main()
