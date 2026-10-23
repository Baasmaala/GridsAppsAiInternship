import unittest

from masar.tests.helpers import ROOT, folder_hashes
from tools.challenges import run_challenges


class Challenges(unittest.TestCase):
    def test_all_five_pass_and_output_is_untouched(self):
        before = folder_hashes(ROOT / "output")
        results = run_challenges()
        self.assertEqual([r["number"] for r in results], [1, 2, 3, 4, 5])
        for r in results:
            self.assertTrue(r["passed"], f"{r['name']}: {r['got']}")
        self.assertEqual(folder_hashes(ROOT / "output"), before)


if __name__ == "__main__":
    unittest.main()
