import json
import tempfile
import unittest
from pathlib import Path

from masar.engine.errors import ResumeError
from masar.engine.executor import resume_run, run_workflow
from masar.engine.runs import list_runs, load_run
from masar.tests.helpers import ROOT, folder_hashes, lesson

GOOD = json.loads((ROOT / "masar" / "samples" / "lessons_good.json").read_text(encoding="utf-8"))


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name) / "output"
        self.store = self.dir / "python_drafts.json"

    def tearDown(self):
        self._tmp.cleanup()

    def drafts(self):
        return json.loads(self.store.read_text(encoding="utf-8"))

    def review_run(self, lessons=GOOD):
        return run_workflow(lessons, store=self.store)["run_id"]

    def record(self, run_id):
        return load_run(self.dir / "runs", run_id)

    def test_review_mode_never_touches_the_drafts_file(self):
        # no drafts file yet: still none after a review run
        self.review_run()
        self.assertFalse(self.store.exists())
        # a drafts file already there: byte for byte the same after a review run
        run_workflow([lesson(source_id="OLD", title="Old one")], approved_by="Trainer", store=self.store)
        before = self.store.read_bytes()
        self.review_run()
        self.assertEqual(self.store.read_bytes(), before)

    def test_review_run_saves_state(self):
        run_id = self.review_run()
        rec = self.record(run_id)
        self.assertEqual(list(rec["pending"]), ["DOR-CAT-001", "DOR-CAT-002", "DOR-CAT-003", "DOR-CAT-004"])
        p = rec["pending"]["DOR-CAT-003"]
        self.assertEqual((p["status"], p["resume_from"]), ("review_pending", "deduplicate"))
        self.assertEqual(p["data"]["title"], "Everyday Verbs")
        self.assertEqual(len(rec["report"]["items"][0]["trace"]), 5)

    def test_dry_run_saves_no_state(self):
        run_workflow(GOOD, dry_run=True, store=self.store)
        self.assertFalse(self.dir.exists())

    def test_resume_all(self):
        run_id = self.review_run()
        result = resume_run(run_id, store=self.store, reviewer="Mona")
        self.assertEqual([i["status"] for i in result["items"]], ["draft_saved"] * 4)
        self.assertEqual(result["still_waiting"], {})
        self.assertEqual([d["reviewed_by"] for d in self.drafts()], ["Mona"] * 4)
        rec = self.record(run_id)
        self.assertEqual(rec["report"]["summary"], {"draft_saved": 4})
        item = rec["report"]["items"][0]
        self.assertEqual(item["steps"], ["validate", "normalize", "count_words", "deduplicate", "approval",
                                         "deduplicate", "approval", "persist", "audit"])

    def test_resume_one_item(self):
        run_id = self.review_run()
        result = resume_run(run_id, store=self.store, reviewer="Mona", items=["DOR-CAT-002"])
        self.assertEqual(result["items"], [{"source_id": "DOR-CAT-002", "status": "draft_saved"}])
        self.assertEqual(len(result["still_waiting"]), 3)
        self.assertEqual([d["source_id"] for d in self.drafts()], ["DOR-CAT-002"])

    def test_cannot_decide_twice(self):
        run_id = self.review_run()
        resume_run(run_id, store=self.store, reviewer="Mona", items=["DOR-CAT-001"])
        with self.assertRaisesRegex(ResumeError, "already decided: draft_saved by Mona"):
            resume_run(run_id, store=self.store, reviewer="Ali", items=["DOR-CAT-001"])
        resume_run(run_id, store=self.store, reviewer="Mona")
        with self.assertRaisesRegex(ResumeError, "nothing waiting"):
            resume_run(run_id, store=self.store, reviewer="Mona")

    def test_reject(self):
        run_id = self.review_run()
        result = resume_run(run_id, store=self.store, reviewer="Mona", decision="reject",
                            reason="level is wrong", items=["DOR-CAT-004"])
        self.assertEqual(result["items"], [{"source_id": "DOR-CAT-004", "status": "rejected"}])
        self.assertFalse(self.store.exists())
        rec = self.record(run_id)
        self.assertEqual(rec["decisions"][0]["reason"], "level is wrong")
        self.assertEqual(rec["report"]["items"][3]["trace"][-1]["note"], "rejected by Mona: level is wrong")

    def test_reject_needs_reason_and_name(self):
        run_id = self.review_run()
        with self.assertRaisesRegex(ResumeError, "reason"):
            resume_run(run_id, store=self.store, reviewer="Mona", decision="reject", reason="  ")
        for name in ("", "   ", None):
            with self.assertRaisesRegex(ResumeError, "reviewer name"):
                resume_run(run_id, store=self.store, reviewer=name)
        self.assertEqual(len(self.record(run_id)["pending"]), 4)

    def test_resume_checks_duplicates_again(self):
        # while run A waits, another run saves the same lessons
        run_a = self.review_run()
        run_workflow(GOOD[:2], approved_by="Ali", store=self.store)
        result = resume_run(run_a, store=self.store, reviewer="Mona")
        self.assertEqual([i["status"] for i in result["items"]],
                         ["skipped_duplicate", "skipped_duplicate", "draft_saved", "draft_saved"])
        self.assertEqual(len(self.drafts()), 4)

    def test_possible_duplicate_needs_item(self):
        run_workflow([lesson(source_id="OLD", title="Greetings")], approved_by="Ali", store=self.store)
        run_id = run_workflow([lesson(source_id="NEW", title="greetings!")], approved_by="Ali",
                              store=self.store)["run_id"]
        self.assertEqual(self.record(run_id)["pending"]["NEW"]["status"], "possible_duplicate")
        with self.assertRaisesRegex(ResumeError, "one by one with --item"):
            resume_run(run_id, store=self.store, reviewer="Mona")
        result = resume_run(run_id, store=self.store, reviewer="Mona", items=["NEW"])
        self.assertEqual(result["items"][0]["status"], "draft_saved")
        self.assertEqual(self.drafts()[1]["possible_duplicate_of"], "OLD")

    def test_blanket_resume_stops_at_new_possible_duplicate(self):
        run_id = self.review_run([lesson(source_id="NEW", title="greetings!")])
        run_workflow([lesson(source_id="OLD", title="Greetings")], approved_by="Ali", store=self.store)
        result = resume_run(run_id, store=self.store, reviewer="Mona")
        self.assertEqual(result["items"][0]["status"], "possible_duplicate")
        self.assertEqual(result["still_waiting"], {"NEW": "possible_duplicate"})

    def test_bad_run_ids(self):
        for bad in ("nope", "../../etc/passwd", "00000000-0000-0000-0000-000000000000"):
            with self.assertRaises(ResumeError):
                resume_run(bad, store=self.store, reviewer="Mona")

    def test_list_runs(self):
        run_id = self.review_run()
        before = folder_hashes(self.dir)
        runs = list_runs(self.dir / "runs")
        self.assertEqual(runs[0]["run_id"], run_id)
        self.assertEqual(len(runs[0]["waiting"]), 4)
        self.assertEqual(folder_hashes(self.dir), before)


if __name__ == "__main__":
    unittest.main()
