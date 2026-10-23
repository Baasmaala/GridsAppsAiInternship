import tempfile
import unittest
from pathlib import Path
from unittest import mock

from masar.engine import registry
from masar.engine.context import Step
from masar.engine.errors import TransientError, ValidationError
from masar.engine.executor import run_workflow
from masar.tests.helpers import base_workflow, lesson


def with_node(node_type):
    wf = base_workflow()
    wf["nodes"].insert(2, {"id": "fetch", "type": node_type})
    wf["edges"] = [[a["id"], b["id"]] for a, b in zip(wf["nodes"], wf["nodes"][1:])]
    return wf


class Flaky:
    # fails with each error in the list, then works
    def __init__(self, *errors):
        self.errors = list(errors)
        self.calls = 0

    def __call__(self, data, run):
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)
        return Step(data)


class RetryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = Path(self._tmp.name) / "python_drafts.json"
        self.waits = []

    def tearDown(self):
        self._tmp.cleanup()

    def run_with(self, node):
        with mock.patch.dict(registry.NODES, {"flaky": node}):
            r = run_workflow([lesson()], approved_by="Trainer", store=self.store,
                             workflow=with_node("flaky"), sleep=self.waits.append)
        return r["items"][0]

    def test_timeout_twice_then_ok(self):
        node = Flaky(TransientError("timeout"), TransientError("503"))
        item = self.run_with(node)
        self.assertEqual(item["status"], "draft_saved")
        self.assertEqual(self.waits, [1, 2])
        self.assertEqual(node.calls, 3)
        attempts = item["trace"][2]["attempts"]
        self.assertEqual(attempts, [{"attempt": 1, "error": "timeout", "wait_s": 1},
                                    {"attempt": 2, "error": "503", "wait_s": 2},
                                    {"attempt": 3, "result": "ok"}])

    def test_gives_up_after_three_retries(self):
        node = Flaky(*[TransientError("timeout") for _ in range(10)])
        item = self.run_with(node)
        self.assertEqual(item["status"], "failed_error")
        self.assertEqual(item["error"], "gave up after 4 attempts: timeout")
        self.assertEqual(self.waits, [1, 2, 4])
        self.assertEqual(node.calls, 4)
        self.assertFalse(self.store.exists())

    def test_retry_after_is_respected(self):
        item = self.run_with(Flaky(TransientError("429", retry_after=5)))
        self.assertEqual(item["status"], "draft_saved")
        self.assertEqual(self.waits, [5])

    def test_long_retry_after_stops_at_once(self):
        # the moneyprinterturbo case: "retry in 13 hours". do not hammer, stop.
        node = Flaky(TransientError("429 quota", retry_after=13 * 3600))
        item = self.run_with(node)
        self.assertEqual(item["status"], "failed_error")
        self.assertEqual(item["error"], "gave up: retry after 13h is too long to wait (429 quota)")
        self.assertEqual(self.waits, [])
        self.assertEqual(node.calls, 1)

    def test_validation_error_is_never_retried(self):
        node = Flaky(ValidationError("title is empty"))
        item = self.run_with(node)
        self.assertEqual(item["status"], "failed_validation")
        self.assertEqual(node.calls, 1)
        self.assertEqual(self.waits, [])

    def test_a_bug_is_not_retried(self):
        node = Flaky(KeyError("x"))
        item = self.run_with(node)
        self.assertEqual(item["status"], "failed_error")
        self.assertEqual(node.calls, 1)
        self.assertEqual(self.waits, [])


if __name__ == "__main__":
    unittest.main()
