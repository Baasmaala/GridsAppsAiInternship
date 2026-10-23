import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from masar.engine import registry
from masar.engine.errors import WorkflowError
from masar.engine.executor import run_workflow
from masar.engine.lint import lint
from masar.tests.helpers import ROOT, lesson

EVIL = ROOT / "masar" / "workflows" / "malicious_example.json"


class MaliciousWorkflow(unittest.TestCase):
    def test_lint_names_every_problem(self):
        errors = lint(json.loads(EVIL.read_text(encoding="utf-8")))
        self.assertIn("workflow: key 'script' is not allowed. workflow.json is a description, not code", errors)
        self.assertIn("node 'sneak': key 'code' is not allowed. workflow.json is a description, not code", errors)
        self.assertTrue(any("node 'sneak': unknown node type 'exec_python'" in e for e in errors))

    def test_no_node_runs_at_all(self):
        spies = {name: mock.Mock(wraps=fn) for name, fn in registry.NODES.items()}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(registry.NODES, spies):
            with self.assertRaises(WorkflowError):
                run_workflow([lesson()], approved_by="Trainer", store=Path(tmp) / "out" / "d.json",
                             workflow_path=EVIL)
            self.assertFalse((Path(tmp) / "out").exists())
        for spy in spies.values():
            spy.assert_not_called()

    def test_cli_refuses_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run([sys.executable, "-m", "masar", "--workflow", str(EVIL), "--approved-by", "Trainer",
                                "--store", str(Path(tmp) / "out" / "d.json")],
                               cwd=ROOT, capture_output=True, encoding="utf-8")
            self.assertEqual(r.returncode, 1)
            self.assertIn("workflow rejected", r.stderr)
            self.assertIn("exec_python", r.stderr)
            self.assertFalse((Path(tmp) / "out").exists())


if __name__ == "__main__":
    unittest.main()
