import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from masar.engine import registry
from masar.engine.errors import StoreError, WorkflowError
from masar.engine.executor import run_workflow
from masar.tests.helpers import (ROOT, base_workflow, chain, folder_hashes, lesson,
                                 without_times, write_json)

GOOD = json.loads((ROOT / "masar" / "samples" / "lessons_good.json").read_text(encoding="utf-8"))
BAD = json.loads((ROOT / "masar" / "samples" / "lessons_bad.json").read_text(encoding="utf-8"))


class TempStore(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name) / "output"
        self.store = self.dir / "python_drafts.json"

    def tearDown(self):
        self._tmp.cleanup()

    def run_wf(self, lessons, **kw):
        return run_workflow(lessons, store=self.store, **kw)

    def drafts(self):
        return json.loads(self.store.read_text(encoding="utf-8"))


class BriefChallenges(TempStore):
    # the 5 challenges from page 5 of the brief

    def test_1_empty_title_fails_and_saves_nothing(self):
        r = self.run_wf([lesson(title="")], approved_by="Trainer")
        self.assertEqual(r["items"][0]["status"], "failed_validation")
        self.assertIn("title", r["items"][0]["error"])
        self.assertFalse(self.store.exists())

    def test_2_approved_twice_is_skipped_duplicate(self):
        first = self.run_wf([lesson()], approved_by="Trainer")
        second = self.run_wf([lesson()], approved_by="Trainer")
        self.assertEqual(first["items"][0]["status"], "draft_saved")
        self.assertEqual(second["items"][0]["status"], "skipped_duplicate")
        self.assertEqual(len(self.drafts()), 1)

    def test_3_no_reviewer_is_review_pending(self):
        r = self.run_wf([lesson()])
        self.assertEqual(r["items"][0]["status"], "review_pending")
        self.assertEqual(r["mode"], "review")
        self.assertFalse(self.store.exists())

    def test_4_dry_run_changes_nothing_in_output(self):
        self.run_wf(GOOD[:2], approved_by="Trainer")
        before = folder_hashes(self.dir)
        r = self.run_wf(GOOD, approved_by="Trainer", dry_run=True)
        self.assertEqual(folder_hashes(self.dir), before)
        self.assertEqual(r["summary"], {"dry_run_preview": 2, "skipped_duplicate": 2})

    def test_4_dry_run_does_not_create_output(self):
        self.run_wf(GOOD, approved_by="Trainer", dry_run=True)
        self.assertFalse(self.dir.exists())

    def test_5_word_count_in_draft_and_report(self):
        r = self.run_wf([lesson(body="Hello! My name is Sara.")], approved_by="Trainer")
        self.assertEqual(r["items"][0]["word_count"], 5)
        self.assertEqual(self.drafts()[0]["word_count"], 5)


class ReviewPromptRules(TempStore):
    # the AI review prompt on page 5, plus the hard rules

    def test_every_saved_record_is_draft(self):
        self.run_wf(GOOD + [lesson(source_id="L9", status="published")], approved_by="Trainer")
        drafts = self.drafts()
        self.assertEqual(len(drafts), 5)
        for d in drafts:
            self.assertEqual(d["status"], "draft")
            self.assertEqual(d["reviewed_by"], "Trainer")
            self.assertIn("saved_at", d)

    def test_level_9a_rejected_and_b1_cleaned(self):
        r = self.run_wf([lesson(source_id="A", level="9A"), lesson(source_id="B", level=" b1 ")],
                        approved_by="Trainer")
        self.assertEqual(r["items"][0]["status"], "failed_validation")
        self.assertIn("Invalid CEFR level", r["items"][0]["error"])
        self.assertEqual(r["items"][1]["status"], "draft_saved")
        self.assertEqual(self.drafts()[0]["level"], "B1")

    def test_all_missing_fields_listed_at_once(self):
        r = self.run_wf([{"source_id": "X", "level": "A1", "language": "en"}])
        self.assertEqual(r["items"][0]["error"], "Missing/empty field: title, category, body")

    def test_same_dry_run_twice_gives_same_report(self):
        a = self.run_wf(GOOD + BAD, approved_by="Trainer", dry_run=True)
        b = self.run_wf(GOOD + BAD, approved_by="Trainer", dry_run=True)
        self.assertEqual(without_times(a), without_times(b))

    def test_language_comes_from_workflow_setting(self):
        arabic = lesson(source_id="AR1", title="التحيات", language="ar", body="مرحبا كيف حالك")
        r = self.run_wf([arabic], approved_by="Trainer")
        self.assertEqual(r["items"][0]["status"], "failed_validation")
        self.assertIn("not allowed", r["items"][0]["error"])

        wf = base_workflow()
        wf["allowed_languages"] = ["en", "ar"]
        r = self.run_wf([arabic], approved_by="Trainer", workflow=wf)
        self.assertEqual(r["items"][0]["status"], "draft_saved")
        self.assertEqual(r["items"][0]["word_count"], 3)
        self.assertEqual(self.drafts()[0]["slug"], "التحيات")

    def test_no_workflow_can_skip_approval(self):
        wf = chain("validate_lesson", "normalize_lesson", "check_duplicate", "save_draft")
        with self.assertRaises(WorkflowError) as cm:
            self.run_wf([lesson()], approved_by="Trainer", workflow=wf)
        self.assertIn("manual_approval", str(cm.exception))
        self.assertFalse(self.dir.exists())


class EngineBehaviour(TempStore):
    def test_good_sample_saves_all(self):
        r = self.run_wf(GOOD, approved_by="Trainer")
        self.assertEqual(r["summary"], {"draft_saved": 4})

    def test_bad_sample_statuses(self):
        r = self.run_wf(BAD, approved_by="Trainer")
        self.assertEqual([i["status"] for i in r["items"]], [
            "failed_validation", "failed_validation", "failed_validation", "failed_validation",
            "failed_validation", "draft_saved", "skipped_duplicate", "failed_validation"])

    def test_normalize_cleans_but_keeps_meaning(self):
        self.run_wf([GOOD[3]], approved_by="Trainer")
        d = self.drafts()[0]
        self.assertEqual(d["title"], "Ordering Food")
        self.assertEqual(d["category"], "75 Daily Conversations")
        self.assertEqual(d["language"], "en")
        self.assertEqual(d["body"], "I would like a cup of tea, please.")
        self.assertEqual(d["tags"], ["food", "cafe"])
        self.assertEqual(d["slug"], "ordering-food")

    def test_same_id_twice_in_one_input_every_mode(self):
        two = [lesson(), lesson()]
        for kw in ({}, {"dry_run": True, "approved_by": "Trainer"}, {"approved_by": "Trainer"}):
            with self.subTest(kw=kw):
                r = self.run_wf(two, **kw)
                self.assertEqual(r["items"][1]["status"], "skipped_duplicate")
                self.assertEqual(r["items"][1]["trace"][-1]["note"],
                                 "source_id came earlier in this input")
        self.assertEqual(len(self.drafts()), 1)

    def test_trace_has_every_node(self):
        r = self.run_wf([lesson(title="  Greetings  ")], approved_by="Trainer")
        trace = r["items"][0]["trace"]
        self.assertEqual([t["node"] for t in trace], r["items"][0]["steps"])
        self.assertEqual(len(trace), 7)
        for t in trace:
            self.assertIn("input", t)
            self.assertIn("output", t)
            self.assertIsInstance(t["ms"], float)
            self.assertEqual(t["result"], "ok")
        self.assertEqual(trace[1]["input"]["title"], "  Greetings  ")
        self.assertEqual(trace[1]["output"]["title"], "Greetings")

    def test_trace_shows_where_it_stopped(self):
        r = self.run_wf([lesson()])
        last = r["items"][0]["trace"][-1]
        self.assertEqual((last["node"], last["result"], last["status"]),
                         ("approval", "stop", "review_pending"))

    def test_bug_in_a_node_is_failed_error(self):
        def boom(data, run):
            if data["source_id"] == "L2":
                raise RuntimeError("something broke")
            return registry.NODES["log_result"](data, run)

        wf = base_workflow()
        wf["nodes"].insert(2, {"id": "boom", "type": "boom"})
        wf["edges"] = [[a["id"], b["id"]] for a, b in zip(wf["nodes"], wf["nodes"][1:])]
        with mock.patch.dict(registry.NODES, {"boom": boom}):
            r = self.run_wf([lesson(source_id=s, title=f"Lesson {s}") for s in ("L1", "L2", "L3")],
                            approved_by="Trainer", workflow=wf)
        self.assertEqual([i["status"] for i in r["items"]],
                         ["draft_saved", "failed_error", "draft_saved"])
        self.assertEqual(r["items"][1]["error"], "RuntimeError: something broke")
        self.assertEqual(len(self.drafts()), 2)

    def test_no_temp_file_left_after_save(self):
        self.run_wf([lesson()], approved_by="Trainer")
        self.assertEqual(sorted(p.name for p in self.dir.iterdir()),
                         ["audit.jsonl", "python_drafts.json", "runs"])
        self.assertEqual([p.suffix for p in (self.dir / "runs").iterdir()], [".json"])
        self.assertFalse(list(self.dir.rglob(".tmp-*")))

    def test_failed_write_keeps_old_file(self):
        self.run_wf([lesson()], approved_by="Trainer")
        before = folder_hashes(self.dir)
        with mock.patch("masar.engine.storage.os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.run_wf([lesson(source_id="L2", title="Other")], approved_by="Trainer")
        self.assertEqual(folder_hashes(self.dir), before)

    def test_file_not_rewritten_when_nothing_new(self):
        self.run_wf([lesson()], approved_by="Trainer")
        mtime = self.store.stat().st_mtime_ns
        with mock.patch("masar.engine.executor.atomic_json_write") as write:
            self.run_wf([lesson()], approved_by="Trainer")
        write.assert_not_called()
        self.assertEqual(self.store.stat().st_mtime_ns, mtime)

    def test_broken_store_is_refused(self):
        write_json(self.store, {"not": "a list"})
        with self.assertRaises(StoreError):
            self.run_wf([lesson()], approved_by="Trainer")

    def test_keeps_drafts_already_saved(self):
        self.run_wf([lesson(source_id="OLD", title="Old one")], approved_by="Ali")
        self.run_wf([lesson(source_id="NEW", title="New one")], approved_by="Mona")
        self.assertEqual([(d["source_id"], d["reviewed_by"]) for d in self.drafts()],
                         [("OLD", "Ali"), ("NEW", "Mona")])


if __name__ == "__main__":
    unittest.main()
