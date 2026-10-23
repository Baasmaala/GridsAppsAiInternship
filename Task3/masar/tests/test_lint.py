import unittest

from masar.engine.errors import WorkflowError
from masar.engine.lint import lint
from masar.engine.loader import load_workflow, parse_workflow, to_mermaid
from masar.engine.executor import DEFAULT_WORKFLOW
from masar.tests.helpers import base_workflow, chain

FULL = ("validate_lesson", "normalize_lesson", "word_count", "check_duplicate",
        "manual_approval", "save_draft", "log_result")


class LintTests(unittest.TestCase):
    def assertRejected(self, wf, text):
        errors = lint(wf)
        self.assertTrue(any(text in e for e in errors), f"{text!r} not in {errors}")

    def test_default_workflow_is_ok(self):
        self.assertEqual(lint(base_workflow()), [])
        wf = load_workflow(DEFAULT_WORKFLOW)
        self.assertEqual(wf.allowed_languages, ["en"])
        self.assertEqual([n["type"] for n in wf.nodes], list(FULL))

    def test_unknown_node_type(self):
        self.assertRejected(chain("validate_lesson", "exec_python"), "unknown node type 'exec_python'")

    def test_code_field_on_node(self):
        wf = chain(*FULL)
        wf["nodes"][0]["code"] = "import os; os.remove('x')"
        self.assertRejected(wf, "key 'code' is not allowed. workflow.json is a description, not code")

    def test_code_field_on_workflow(self):
        self.assertRejected(chain(*FULL, script="rm -rf /"), "key 'script' is not allowed")

    def test_unknown_key(self):
        wf = chain(*FULL)
        wf["nodes"][1]["color"] = "red"
        self.assertRejected(wf, "unknown key 'color'")

    def test_cycle(self):
        wf = chain(*FULL)
        wf["edges"].append(["n7", "n1"])
        self.assertRejected(wf, "cycle found: n1 -> n2")
        wf = chain("validate_lesson", "normalize_lesson", "log_result")
        wf["edges"] = [["n1", "n2"], ["n2", "n3"], ["n3", "n2"]]
        self.assertRejected(wf, "more than one node before it")
        wf["edges"] = [["n2", "n3"], ["n3", "n2"]]
        self.assertRejected(wf, "cycle found: n2 -> n3 -> n2")
        wf["edges"] = [["n1", "n1"]]
        self.assertRejected(wf, "cycle found: n1 -> n1")

    def test_missing_edge_target(self):
        wf = chain(*FULL)
        wf["edges"][-1] = ["n6", "ghost"]
        self.assertRejected(wf, "points to a missing node 'ghost'")

    def test_duplicate_node_id(self):
        wf = chain(*FULL)
        wf["nodes"][1]["id"] = "n1"
        self.assertRejected(wf, "node 'n1': duplicate node id")

    def test_branch_is_not_linear(self):
        wf = chain(*FULL)
        wf["edges"].append(["n1", "n3"])
        self.assertRejected(wf, "n1' has more than one next node")

    def test_separate_parts(self):
        wf = chain(*FULL)
        del wf["edges"][2]
        self.assertRejected(wf, "2 separate parts")

    def test_bad_edge_shape(self):
        wf = chain(*FULL)
        wf["edges"][0] = "n1->n2"
        self.assertRejected(wf, "edge 1: must be a [from, to] pair")

    def test_save_needs_approval_before_it(self):
        self.assertRejected(chain("validate_lesson", "normalize_lesson", "check_duplicate", "save_draft"),
                            "no human approval, no save")
        # approval after save does not count
        self.assertRejected(chain("validate_lesson", "normalize_lesson", "check_duplicate",
                                  "save_draft", "manual_approval"), "no human approval, no save")

    def test_save_needs_duplicate_check(self):
        self.assertRejected(chain("validate_lesson", "normalize_lesson", "manual_approval", "save_draft"),
                            "save_draft needs a check_duplicate node before it")

    def test_trigger_must_be_manual(self):
        wf = chain(*FULL)
        wf["trigger"] = {"type": "webhook"}
        self.assertRejected(wf, "trigger: type must be 'manual'")

    def test_allowed_languages_shape(self):
        for bad in ([], "en", [""], [1]):
            with self.subTest(bad=bad):
                self.assertRejected(chain(*FULL, allowed_languages=bad), "allowed_languages")

    def test_edges_order_wins_over_nodes_order(self):
        wf = chain(*FULL)
        wf["nodes"].reverse()
        parsed = parse_workflow(wf)
        self.assertEqual([n["type"] for n in parsed.nodes], list(FULL))

    def test_parse_raises_with_all_errors(self):
        wf = chain("validate_lesson", "exec_python")
        wf["nodes"][0]["eval"] = "1"
        with self.assertRaises(WorkflowError) as cm:
            parse_workflow(wf)
        self.assertEqual(len(cm.exception.errors), 2)

    def test_mermaid(self):
        text = to_mermaid(load_workflow(DEFAULT_WORKFLOW))
        self.assertTrue(text.startswith("flowchart LR"))
        self.assertIn('n5["approval<br/>manual_approval"]', text)
        self.assertIn("n6 --> n7", text)


if __name__ == "__main__":
    unittest.main()
