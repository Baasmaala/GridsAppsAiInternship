import hashlib
import json
import tempfile
import unittest
from pathlib import Path

try:
    from fastapi.testclient import TestClient

    from api.app import create_app
except ImportError:  # plain python without the venv: the engine tests still run
    TestClient = None

NEEDS_FASTAPI = unittest.skipUnless(TestClient, "fastapi is not installed (use: uv run python -m unittest)")
GOOD_RUN = {"workflow": "dorosak_lessons", "sample": "lessons_good"}


def hashes(folder):
    if not folder.exists():
        return None
    return {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob("*")) if p.is_file()}


@NEEDS_FASTAPI
class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.output = Path(self._tmp.name) / "output"
        self.client = TestClient(create_app(self.output), base_url="http://127.0.0.1")

    def tearDown(self):
        self.client.close()
        self._tmp.cleanup()

    def post(self, url, body=None, **kw):
        return self.client.post(url, json=body, **kw)

    def review_run(self, sample="lessons_good"):
        r = self.post("/api/runs", {"workflow": "dorosak_lessons", "sample": sample})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def decide(self, run_id, sid, **body):
        return self.post(f"/api/reviews/{run_id}/{sid}", {"decision": "approve", **body})

    def drafts_file(self):
        return self.output / "python_drafts.json"


class Workflows(ApiTestCase):
    def test_list(self):
        got = {w["key"]: w["ok"] for w in self.client.get("/api/workflows").json()}
        self.assertEqual(got, {"dorosak_lessons": True, "malicious_example": False, "question_bank": True})

    def test_one(self):
        w = self.client.get("/api/workflows/dorosak_lessons").json()
        self.assertEqual(len(w["nodes"]), 7)
        self.assertTrue(w["mermaid"].startswith("flowchart LR"))
        self.assertEqual(w["allowed_languages"], ["en"])

    def test_malicious_is_shown_with_errors(self):
        w = self.client.get("/api/workflows/malicious_example").json()
        self.assertFalse(w["ok"])
        self.assertTrue(any("exec_python" in e for e in w["errors"]))
        self.assertNotIn("mermaid", w)

    def test_unknown_and_path_tricks(self):
        for key in ("nope", "..%2F..%2Fpyproject", "DOROSAK_LESSONS", "a.b"):
            self.assertEqual(self.client.get(f"/api/workflows/{key}").status_code, 404, key)


class Samples(ApiTestCase):
    def upload(self, name, content):
        body = content if isinstance(content, bytes) else json.dumps(content).encode()
        return self.client.post(f"/api/samples/upload?name={name}", content=body,
                                headers={"Content-Type": "application/json"})

    def test_list_builtin(self):
        keys = [s["key"] for s in self.client.get("/api/samples").json()]
        self.assertEqual(keys, ["lessons_bad", "lessons_good", "lessons_similar", "questions"])

    def test_upload_and_run(self):
        lessons = [{"source_id": "UP-1", "title": "Uploaded", "category": "c", "level": "A1",
                    "language": "en", "body": "one two"}]
        r = self.upload("my_lessons", lessons)
        self.assertEqual((r.status_code, r.json()), (201, {"key": "upload:my_lessons", "items": 1}))
        self.assertIn("upload:my_lessons", [s["key"] for s in self.client.get("/api/samples").json()])
        r = self.post("/api/runs", {"workflow": "dorosak_lessons", "sample": "upload:my_lessons", "dry_run": True})
        self.assertEqual(r.json()["items"][0]["word_count"], 2)

    def test_upload_refused(self):
        cases = [("bad name!", [{}], 422), ("../x", [{}], 422), ("x", b"not json", 422),
                 ("x", {"a": 1}, 422), ("x", [1, {}], 422), ("x", [{}] * 501, 422),
                 ("x", b"[" + b'{"a": "' + b"x" * 210_000 + b'"}]', 413)]
        for name, content, code in cases:
            with self.subTest(name=name, code=code):
                self.assertEqual(self.upload(name, content).status_code, code)
        self.assertFalse((self.output / "uploads").exists())

    def test_unknown_sample(self):
        r = self.post("/api/runs", {**GOOD_RUN, "sample": "upload:../../secrets"})
        self.assertEqual(r.status_code, 404)


class Runs(ApiTestCase):
    def test_dry_run_writes_nothing(self):
        r = self.post("/api/runs", {**GOOD_RUN, "dry_run": True, "approved_by": "Trainer"})
        self.assertEqual(r.json()["summary"], {"dry_run_preview": 4})
        self.assertEqual(len(r.json()["items"][0]["trace"]), 7)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.client.get("/api/runs").json(), [])

    def test_dry_run_does_not_change_output(self):
        run_id = self.review_run()["run_id"]
        self.decide(run_id, "DOR-CAT-001", reviewer="Mona")
        before = hashes(self.output)
        for body in ({**GOOD_RUN, "dry_run": True, "approved_by": "Trainer"}, {**GOOD_RUN, "dry_run": True}):
            self.post("/api/runs", body)
            self.assertEqual(hashes(self.output), before)

    def test_approved_by_only_with_dry_run(self):
        r = self.post("/api/runs", {**GOOD_RUN, "approved_by": "Trainer"})
        self.assertEqual(r.status_code, 422)
        self.assertIn("only allowed with dry_run", r.json()["detail"])
        self.assertFalse(self.output.exists())

    def test_review_run_is_listed(self):
        report = self.review_run()
        self.assertEqual(report["summary"], {"review_pending": 4})
        runs = self.client.get("/api/runs").json()
        self.assertEqual([r["run_id"] for r in runs], [report["run_id"]])
        one = self.client.get(f"/api/runs/{report['run_id']}").json()
        self.assertEqual(len(one["waiting"]), 4)
        self.assertEqual(len(one["report"]["items"][0]["trace"]), 5)
        self.assertFalse(self.drafts_file().exists())

    def test_strict_body(self):
        for body in ({**GOOD_RUN, "publish": True}, {**GOOD_RUN, "dry_run": "no"},
                     {**GOOD_RUN, "dry_run": 0}, {"workflow": "dorosak_lessons"}):
            with self.subTest(body=body):
                self.assertEqual(self.post("/api/runs", body).status_code, 422)
        self.assertFalse(self.output.exists())

    def test_malicious_cannot_run(self):
        r = self.post("/api/runs", {"workflow": "malicious_example", "sample": "lessons_good", "dry_run": True})
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.json()["detail"], "workflow rejected")
        self.assertTrue(any("not code" in e for e in r.json()["errors"]))
        self.assertFalse(self.output.exists())

    def test_bad_lessons_are_statuses_not_errors(self):
        r = self.post("/api/runs", {"workflow": "dorosak_lessons", "sample": "lessons_bad", "dry_run": True})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["summary"]["failed_validation"], 6)

    def test_unknown_run(self):
        for run_id in ("nope", "00000000-0000-0000-0000-000000000000"):
            self.assertEqual(self.client.get(f"/api/runs/{run_id}").status_code, 404)


class Reviews(ApiTestCase):
    def test_inbox(self):
        self.review_run()
        inbox = self.client.get("/api/reviews").json()
        self.assertEqual([i["source_id"] for i in inbox], ["DOR-CAT-001", "DOR-CAT-002", "DOR-CAT-003", "DOR-CAT-004"])
        four = inbox[3]
        self.assertEqual(four["original"]["title"], "  Ordering   Food  ")
        self.assertEqual(four["normalized"]["title"], "Ordering Food")
        self.assertEqual(four["word_count"], 8)
        self.assertEqual(four["status"], "review_pending")

    def test_approve_one(self):
        run_id = self.review_run()["run_id"]
        r = self.decide(run_id, "DOR-CAT-002", reviewer="Mona")
        self.assertEqual(r.json()["items"], [{"source_id": "DOR-CAT-002", "status": "draft_saved"}])
        drafts = self.client.get("/api/drafts").json()
        self.assertEqual([(d["file"], d["draft"]["source_id"], d["draft"]["status"]) for d in drafts],
                         [("python_drafts.json", "DOR-CAT-002", "draft")])
        self.assertEqual(len(self.client.get("/api/reviews").json()), 3)

    def test_needs_a_name(self):
        run_id = self.review_run()["run_id"]
        for name in ("", "   "):
            r = self.decide(run_id, "DOR-CAT-001", reviewer=name)
            self.assertEqual(r.status_code, 409)
            self.assertIn("reviewer name", r.json()["detail"])
        self.assertEqual(self.post(f"/api/reviews/{run_id}/DOR-CAT-001", {"decision": "approve"}).status_code, 422)
        self.assertFalse(self.drafts_file().exists())

    def test_decide_once(self):
        run_id = self.review_run()["run_id"]
        self.decide(run_id, "DOR-CAT-001", reviewer="Mona")
        r = self.decide(run_id, "DOR-CAT-001", reviewer="Ali")
        self.assertEqual(r.status_code, 409)
        self.assertIn("already decided: draft_saved by Mona", r.json()["detail"])

    def test_reject_needs_reason(self):
        run_id = self.review_run()["run_id"]
        r = self.decide(run_id, "DOR-CAT-001", reviewer="Mona", decision="reject")
        self.assertEqual((r.status_code, r.json()["detail"]), (409, "a reason is needed to reject"))
        r = self.decide(run_id, "DOR-CAT-001", reviewer="Mona", decision="reject", reason="not for A1")
        self.assertEqual(r.json()["items"][0]["status"], "rejected")
        self.assertFalse(self.drafts_file().exists())

    def test_possible_duplicate_shows_old_draft(self):
        run_id = self.review_run()["run_id"]
        self.decide(run_id, "DOR-CAT-001", reviewer="Mona")
        up = [{"source_id": "DOR-CAT-901", "title": "greetings, and introductions!", "category": "c",
               "level": "A1", "language": "en", "body": "hello"}]
        self.client.post("/api/samples/upload?name=lookalike", content=json.dumps(up))
        self.post("/api/runs", {"workflow": "dorosak_lessons", "sample": "upload:lookalike"})
        item = [i for i in self.client.get("/api/reviews").json() if i["source_id"] == "DOR-CAT-901"][0]
        self.assertEqual(item["status"], "possible_duplicate")
        self.assertEqual(item["old_draft"]["source_id"], "DOR-CAT-001")
        self.assertEqual(item["old_draft"]["status"], "draft")
        r = self.decide(item["run_id"], "DOR-CAT-901", reviewer="Mona")
        self.assertEqual(r.json()["items"][0]["status"], "draft_saved")

    def test_unknown(self):
        self.assertEqual(self.decide("nope", "X", reviewer="Mona").status_code, 404)
        run_id = self.review_run()["run_id"]
        self.assertEqual(self.decide(run_id, "NOT-THERE", reviewer="Mona").status_code, 409)

    def test_question_bank_inbox(self):
        self.post("/api/runs", {"workflow": "question_bank", "sample": "questions"})
        inbox = self.client.get("/api/reviews").json()
        self.assertEqual({i["source_id"]: i["status"] for i in inbox},
                         {"TC-Q-001": "review_pending", "TC-Q-002": "review_pending",
                          "TC-Q-009": "possible_duplicate"})
        self.assertIsNone(inbox[2]["old_draft"])  # the look-alike is in the same run, not saved yet
        self.decide(inbox[0]["run_id"], "TC-Q-001", reviewer="Mona")
        self.assertTrue((self.output / "python_question-bank_drafts.json").exists())


class AuditAndLab(ApiTestCase):
    def test_audit_and_verify(self):
        run_id = self.review_run()["run_id"]
        self.decide(run_id, "DOR-CAT-001", reviewer="Mona")
        lines = self.client.get("/api/audit").json()
        self.assertEqual([x["event"] for x in lines], ["run"] * 4 + ["approve"])
        self.assertEqual(self.client.get("/api/audit/verify").json(), {"ok": True, "lines": 5})
        audit = self.output / "audit.jsonl"
        audit.write_text(audit.read_text(encoding="utf-8").replace("Mona", "Boss"), encoding="utf-8")
        v = self.client.get("/api/audit/verify").json()
        self.assertEqual((v["ok"], v["broken_line"]), (False, 5))

    def test_challenges(self):
        r = self.post("/api/challenges/run").json()
        self.assertEqual((r["passed"], r["total"]), (5, 5))
        self.assertEqual([c["name"] for c in r["results"]],
                         ["Fault Injection", "Idempotency", "Review Gate", "Dry Run", "New Node"])
        self.assertFalse(self.output.exists())

    def test_reset(self):
        self.review_run()
        self.assertEqual(self.post("/api/demo/reset", {}).status_code, 422)
        self.assertEqual(self.post("/api/demo/reset", {"confirm": "yes"}).status_code, 422)
        r = self.post("/api/demo/reset", {"confirm": "reset"}).json()
        self.assertEqual(r, {"cleared": True, "seeded": None})
        self.assertFalse(self.output.exists())

    def test_reset_with_seed(self):
        r = self.post("/api/demo/reset", {"confirm": "reset", "seed": True}).json()
        self.assertEqual(r["seeded"]["summary"], {"review_pending": 4})
        self.assertEqual(len(self.client.get("/api/reviews").json()), 4)
        self.assertFalse(self.drafts_file().exists())

    def test_reset_only_deletes_a_folder_called_output(self):
        other = Path(self._tmp.name) / "important"
        other.mkdir()
        (other / "keep.txt").write_text("keep")
        client = TestClient(create_app(other), base_url="http://127.0.0.1")
        self.assertEqual(client.post("/api/demo/reset", json={"confirm": "reset"}).status_code, 422)
        self.assertTrue((other / "keep.txt").exists())


class LocalOnly(ApiTestCase):
    def test_other_host_is_refused(self):
        for host in ("evil.example", "192.168.1.5", "127.0.0.1.evil.example"):
            r = self.client.get("/api/workflows", headers={"Host": host})
            self.assertEqual(r.status_code, 400, host)
        self.assertEqual(self.client.get("/api/workflows", headers={"Host": "localhost:8000"}).status_code, 200)

    def test_cors_only_for_the_web_app(self):
        ok = self.client.get("/api", headers={"Origin": "http://localhost:5173"})
        self.assertEqual(ok.headers.get("access-control-allow-origin"), "http://localhost:5173")
        bad = self.client.get("/api", headers={"Origin": "http://evil.example"})
        self.assertIsNone(bad.headers.get("access-control-allow-origin"))

    def test_host_is_fixed(self):
        from api.__main__ import HOST
        self.assertEqual(HOST, "127.0.0.1")

    def test_every_saved_record_is_a_draft(self):
        run_id = self.review_run()["run_id"]
        for sid in ("DOR-CAT-001", "DOR-CAT-002", "DOR-CAT-003", "DOR-CAT-004"):
            self.decide(run_id, sid, reviewer="Mona")
        saved = json.loads(self.drafts_file().read_text(encoding="utf-8"))
        self.assertEqual({d["status"] for d in saved}, {"draft"})


if __name__ == "__main__":
    unittest.main()
