import json
import tempfile
import unittest
from pathlib import Path

from masar.engine.executor import run_workflow
from masar.engine.lint import lint
from masar.engine.loader import load_workflow
from masar.tests.helpers import ROOT, chain

WORKFLOW = ROOT / "masar" / "workflows" / "question_bank.json"
QUESTIONS = json.loads((ROOT / "masar" / "samples" / "questions.json").read_text(encoding="utf-8"))
GOOD_Q = QUESTIONS[0]


def question(**changes):
    return {**GOOD_Q, **changes}


class QuestionBank(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = Path(self._tmp.name) / "questions.json"

    def tearDown(self):
        self._tmp.cleanup()

    def run_q(self, items, **kw):
        return run_workflow(items, store=self.store, workflow_path=WORKFLOW, **kw)

    def test_workflow_is_ok(self):
        wf = load_workflow(WORKFLOW)
        self.assertEqual([n["type"] for n in wf.nodes], ["validate_question", "normalize_question",
                                                         "check_duplicate", "manual_approval",
                                                         "save_draft", "log_result"])

    def test_sample(self):
        r = self.run_q(QUESTIONS, approved_by="Trainer")
        got = [(i["source_id"], i["status"], i.get("error", "")) for i in r["items"]]
        self.assertEqual(got, [
            ("TC-Q-001", "draft_saved", ""),
            ("TC-Q-002", "draft_saved", ""),
            ("TC-Q-003", "failed_validation", "options must be a list of exactly 4 answers (got 3)"),
            ("TC-Q-004", "failed_validation", "options repeat: red"),
            ("TC-Q-005", "failed_validation", "answer must be the number of the right option, 0 to 3 (got 4)"),
            ("TC-Q-006", "failed_validation", "answer must be the number of the right option, 0 to 3 (got True)"),
            ("TC-Q-007", "failed_validation", "option 2 is empty"),
            ("TC-Q-008", "failed_validation", "Missing/empty field: topic"),
            ("TC-Q-009", "possible_duplicate", ""),
            ("TC-Q-001", "skipped_duplicate", ""),
        ])
        self.assertEqual(r["items"][8]["possible_duplicate_of"], "TC-Q-001")

    def test_normalize_keeps_only_known_fields(self):
        self.run_q([question(source_id="X", status="published", secret="no")], approved_by="Trainer")
        self.run_q([QUESTIONS[1]], approved_by="Trainer")
        saved = json.loads(self.store.read_text(encoding="utf-8"))
        self.assertNotIn("secret", saved[0])
        self.assertEqual(saved[0]["status"], "draft")
        q = saved[1]
        self.assertEqual((q["question"], q["options"][0], q["level"], q["topic"]),
                         ("What is the past of 'buy'?", "bought", "A2", "Irregular verbs"))

    def test_review_gate_and_dry_run_work_the_same(self):
        self.assertEqual(self.run_q([GOOD_Q])["items"][0]["status"], "review_pending")
        r = self.run_q([GOOD_Q], approved_by="Trainer", dry_run=True)
        self.assertEqual(r["items"][0]["status"], "dry_run_preview")
        self.assertFalse(self.store.exists())

    def test_many_problems_at_once(self):
        r = self.run_q([question(options=["a", "a", "b", "c"], answer=-1, level="Z9")])
        error = r["items"][0]["error"]
        for part in ("options repeat: a", "0 to 3 (got -1)", "Invalid CEFR level 'Z9'"):
            self.assertIn(part, error)

    def test_save_needs_a_validator(self):
        errors = lint(chain("check_duplicate", "manual_approval", "save_draft"))
        self.assertIn("save_draft needs a validate node before it (nothing unchecked is saved)", errors)
        self.assertIn("check_duplicate needs a validate node before it", errors)


if __name__ == "__main__":
    unittest.main()
