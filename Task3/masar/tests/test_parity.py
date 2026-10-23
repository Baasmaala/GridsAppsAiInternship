import importlib.util
import shutil
import subprocess
import sys
import unittest

from masar.tests.helpers import ROOT

spec = importlib.util.spec_from_file_location("parity_check", ROOT / "tools" / "parity_check.py")
parity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parity)


def report(*statuses):
    items = [{"source_id": f"L{i}", "status": s, "error": f"text {i}"} for i, s in enumerate(statuses)]
    return {"items": items, "summary": {s: statuses.count(s) for s in set(statuses)}}


class CompareCatchesDifferences(unittest.TestCase):
    def test_same_statuses_match(self):
        rows, summary_ok = parity.compare(report("draft_saved", "failed_validation"),
                                          report("draft_saved", "failed_validation"))
        self.assertTrue(summary_ok)
        self.assertTrue(all(r[3] for r in rows))

    def test_error_text_is_not_compared(self):
        a, b = report("failed_validation"), report("failed_validation")
        b["items"][0]["error"] = "other words"
        self.assertTrue(parity.compare(a, b)[0][0][3])

    def test_different_status_is_caught(self):
        rows, summary_ok = parity.compare(report("draft_saved", "failed_error"),
                                          report("draft_saved", "failed_validation"))
        self.assertFalse(summary_ok)
        self.assertEqual([r[3] for r in rows], [True, False])

    def test_missing_item_is_caught(self):
        rows, summary_ok = parity.compare(report("draft_saved", "draft_saved"), report("draft_saved"))
        self.assertFalse(summary_ok)
        self.assertEqual(rows[1][2], "-")
        self.assertFalse(rows[1][3])


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class NodeEngine(unittest.TestCase):
    def test_node_masar_tests(self):
        r = subprocess.run(["node", "--test"], cwd=ROOT / "masar" / "node",
                           capture_output=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_parity_check(self):
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "parity_check.py")], cwd=ROOT,
                           capture_output=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("output/ untouched: yes", r.stdout)


if __name__ == "__main__":
    unittest.main()
