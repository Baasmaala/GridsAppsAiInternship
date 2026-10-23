import json
import tempfile
import unittest
from pathlib import Path

from masar.engine.errors import WorkflowError
from masar.engine.executor import run_workflow
from masar.tests.helpers import chain, lesson


# the 3 bugs from docs/NOTES.md "Bugs I found in the starter"
class StarterBugs(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = Path(self._tmp.name) / "python_drafts.json"

    def tearDown(self):
        self._tmp.cleanup()

    def test_1_spaces_only_reviewer_is_no_reviewer(self):
        for name in ("   ", "\t", ""):
            with self.subTest(name=repr(name)):
                r = run_workflow([lesson()], approved_by=name, store=self.store)
                self.assertEqual(r["items"][0]["status"], "review_pending")
                self.assertEqual(r["mode"], "review")
                self.assertFalse(self.store.exists())

    def test_1_reviewer_name_is_trimmed(self):
        run_workflow([lesson()], approved_by="  Trainer ", store=self.store)
        saved = json.loads(self.store.read_text(encoding="utf-8"))
        self.assertEqual(saved[0]["reviewed_by"], "Trainer")

    def test_2_normalize_before_validate_is_refused(self):
        wf = chain("normalize_lesson", "validate_lesson", "check_duplicate",
                   "manual_approval", "save_draft")
        with self.assertRaises(WorkflowError) as cm:
            run_workflow([lesson()], approved_by="Trainer", store=self.store, workflow=wf)
        self.assertIn("normalize_lesson needs a validate_lesson node before it", str(cm.exception))

    def test_3_non_object_lessons_do_not_stop_the_run(self):
        r = run_workflow(["hello", 5, None, [1], lesson()], approved_by="Trainer", store=self.store)
        self.assertEqual([i["status"] for i in r["items"]], ["failed_validation"] * 4 + ["draft_saved"])
        self.assertEqual(r["items"][0]["error"], "Lesson must be an object")
        self.assertEqual(r["items"][0]["source_id"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
