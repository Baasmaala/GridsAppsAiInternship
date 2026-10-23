import tempfile
import unittest
from pathlib import Path
from engine import run_workflow

ITEM = {"source_id":"L1", "title":"Greetings", "category":"Conversations",
        "level":"A1", "language":"en", "body":"Hello!"}

class WorkflowTests(unittest.TestCase):
    def test_approval_is_required(self):
        with tempfile.TemporaryDirectory() as td:
            store = Path(td) / "store.json"
            result = run_workflow([ITEM], store=store)
            self.assertEqual(result["items"][0]["status"], "review_pending")
            self.assertFalse(store.exists())

    def test_idempotent_and_draft_only(self):
        with tempfile.TemporaryDirectory() as td:
            store = Path(td) / "store.json"
            first = run_workflow([ITEM], approved_by="Trainer", store=store)
            second = run_workflow([ITEM], approved_by="Trainer", store=store)
            self.assertEqual(first["items"][0]["status"], "draft_saved")
            self.assertEqual(second["items"][0]["status"], "skipped_duplicate")
            self.assertIn('"status": "draft"', store.read_text())

    def test_invalid_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            bad = dict(ITEM, title="")
            result = run_workflow([bad], approved_by="Trainer", store=Path(td) / "db.json")
            self.assertEqual(result["items"][0]["status"], "failed_validation")

    def test_dry_run_does_not_write(self):
        with tempfile.TemporaryDirectory() as td:
            store = Path(td) / "store.json"
            result = run_workflow([ITEM], approved_by="Trainer", dry_run=True, store=store)
            self.assertEqual(result["items"][0]["status"], "dry_run_preview")
            self.assertFalse(store.exists())

if __name__ == "__main__":
    unittest.main()
