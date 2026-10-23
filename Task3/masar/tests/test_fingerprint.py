import json
import tempfile
import unittest
from pathlib import Path

from masar.engine.executor import run_workflow
from masar.engine.fingerprint import clean_for_compare, fingerprint
from masar.tests.helpers import ROOT, base_workflow, lesson, write_json

SIMILAR = json.loads((ROOT / "masar" / "samples" / "lessons_similar.json").read_text(encoding="utf-8"))


def en_ar():
    wf = base_workflow()
    wf["allowed_languages"] = ["en", "ar"]
    return wf


class CleanForCompare(unittest.TestCase):
    def test_english(self):
        self.assertEqual(clean_for_compare("  Greetings, and  INTRODUCTIONS! "), "greetings and introductions")
        self.assertEqual(clean_for_compare("Ask-for: directions?"), "ask for directions")

    def test_arabic(self):
        cases = [("التَّحِيّـات", "التحيات"),      # tashkeel and tatweel
                 ("أحمد إلى آدم ٱلبيت", "احمد الي ادم البيت"),  # alef forms, ى
                 ("مكتبة", "مكتبه"),              # ة
                 ("الي", "الي")]
        for text, want in cases:
            with self.subTest(text=text):
                self.assertEqual(clean_for_compare(text), want)

    def test_same_print_for_same_title(self):
        self.assertEqual(fingerprint("مكتبة المدرسة"), fingerprint("مكتبه  المدرسه"))
        self.assertEqual(fingerprint("Greetings and Introductions"), fingerprint("greetings, and introductions!"))
        self.assertNotEqual(fingerprint("Greetings"), fingerprint("Greeting"))

    def test_no_print_for_no_letters(self):
        for text in ("", "   ", "!!!", None, 5):
            self.assertIsNone(fingerprint(text))


class PossibleDuplicate(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = Path(self._tmp.name) / "output" / "python_drafts.json"

    def tearDown(self):
        self._tmp.cleanup()

    def drafts(self):
        return json.loads(self.store.read_text(encoding="utf-8"))

    def test_similar_sample(self):
        r = run_workflow(SIMILAR, approved_by="Trainer", dry_run=True, store=self.store, workflow=en_ar())
        got = {i["source_id"]: (i["status"], i.get("possible_duplicate_of")) for i in r["items"]}
        self.assertEqual(got, {
            "DOR-SIM-001": ("dry_run_preview", None),
            "DOR-SIM-002": ("possible_duplicate", "DOR-SIM-001"),
            "DOR-SIM-003": ("dry_run_preview", None),
            "DOR-SIM-004": ("possible_duplicate", "DOR-SIM-003"),
            "DOR-SIM-005": ("dry_run_preview", None),
            "DOR-SIM-006": ("possible_duplicate", "DOR-SIM-005"),
            "DOR-SIM-007": ("dry_run_preview", None),
            "DOR-SIM-008": ("possible_duplicate", "DOR-SIM-007"),
            "DOR-SIM-009": ("dry_run_preview", None),
        })

    def test_approved_run_does_not_save_possible_duplicate(self):
        run_workflow([lesson(source_id="OLD", title="Greetings")], approved_by="Trainer", store=self.store)
        r = run_workflow([lesson(source_id="NEW", title="GREETINGS!")], approved_by="Trainer", store=self.store)
        self.assertEqual(r["items"][0]["status"], "possible_duplicate")
        self.assertEqual(r["items"][0]["possible_duplicate_of"], "OLD")
        self.assertEqual([d["source_id"] for d in self.drafts()], ["OLD"])

    def test_stored_text_is_not_changed(self):
        run_workflow([lesson(title="التَّحِيّات", language="ar")], approved_by="Trainer",
                     store=self.store, workflow=en_ar())
        d = self.drafts()[0]
        self.assertEqual(d["title"], "التَّحِيّات")
        self.assertEqual(d["title_fingerprint"], fingerprint("التحيات"))

    def test_old_drafts_without_fingerprint_still_match(self):
        write_json(self.store, [{"source_id": "OLD", "title": "Greetings", "status": "draft"}])
        r = run_workflow([lesson(source_id="NEW", title="greetings")], dry_run=True, store=self.store)
        self.assertEqual(r["items"][0]["possible_duplicate_of"], "OLD")

    def test_same_id_still_wins(self):
        run_workflow([lesson()], approved_by="Trainer", store=self.store)
        r = run_workflow([lesson()], approved_by="Trainer", store=self.store)
        self.assertEqual(r["items"][0]["status"], "skipped_duplicate")
        self.assertNotIn("possible_duplicate_of", r["items"][0])


if __name__ == "__main__":
    unittest.main()
