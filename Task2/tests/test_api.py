# Tests for the API, with FAKE_MODEL=1 (no API key, no requests).
# Run: uv run python tests/test_api.py

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["FAKE_MODEL"] = "1"

from fastapi.testclient import TestClient

import ask
import tutor
from api.main import app

client = TestClient(app)


def send(thread, sentence):
    return client.post("/chat", json={"thread_id": thread, "sentence": sentence})


def ask_maher(thread, question, context=None):
    body = {"thread_id": thread, "question": question}
    if context:
        body["context"] = context
    return client.post("/ask", json=body)


def calls():
    return tutor.checker.calls + tutor.retry_checker.calls + ask.asker.calls


def test_check():
    r = send("t1", "Yesterday i goed to school.").json()
    assert r["kind"] == "check"
    assert {e["wrong"] for e in r["errors"]} == {"i", "goed"}
    assert all(e["reason_en"] for e in r["errors"])
    assert {m["wrong"] for m in r["mistakes"]} == {"i", "goed"}
    assert r["mistakes"][0]["sentence"] == "Yesterday i goed to school."
    assert r["corrected"] == "Yesterday I went to school."
    assert r["fixing"] == {"tries": 0, "max_tries": 2}


def test_correct_sentence():
    r = send("t2", "She has an apple.").json()
    assert r["errors"] == [] and r["fixing"] is None


def test_almost_then_correct():
    send("t3", "She have a apple.")
    r = send("t3", "She has a apple.").json()
    assert r["kind"] == "retry" and r["status"] == "almost"
    assert r["hint"] and r["corrected"] == ""  # no answer in the hint step
    assert r["still_wrong"] == ["a apple"]  # only the wrong words
    assert r["fixing"] == {"tries": 1, "max_tries": 2}
    r = send("t3", "She has an apple.").json()
    assert r["status"] == "correct" and r["fixing"] is None


def test_fixed_but_new_mistake():
    before = calls()
    send("n1", "She have a cat.")
    r = send("n1", "She has a cat and I ate a apple.").json()
    assert calls() == before + 2  # still 1 call per try
    assert r["status"] == "fixed_new"
    assert [e["wrong"] for e in r["errors"]] == ["a apple"]
    assert r["corrected"] == "She has a cat and I ate an apple."
    assert r["fixing"] == {"tries": 0, "max_tries": 2}  # a new fix step
    learned = {m["wrong"]: m["learned"] for m in r["mistakes"]}
    assert learned == {"She have": True, "a apple": False}
    r = send("n1", "She has a cat and I ate an apple.").json()
    assert r["status"] == "correct"


def test_almost_with_new_mistake():
    send("n2", "She have a cat.")
    r = send("n2", "She have a cat and a apple.").json()
    assert r["status"] == "almost"
    assert set(r["still_wrong"]) == {"She have", "a apple"}  # old and new, no answers
    assert r["corrected"] == "" and r["errors"] == []
    r = send("n2", "She have a cat and a apple.").json()
    assert r["status"] == "gave_up"
    assert r["corrected"] == "She has a cat and an apple."  # the new fix is in it too


def test_gave_up():
    send("t4", "He don't like it.")
    send("t4", "He don't like it.")
    r = send("t4", "He don't like it.").json()
    assert r["status"] == "gave_up" and r["corrected"] == "He doesn't like it."


def test_skip():
    send("t5", "I buyed a book.")
    r = send("t5", "skip").json()
    assert r["status"] == "skipped" and r["corrected"] == "I bought a book."


def test_threads_are_apart():
    send("t6", "I buyed a book.")
    r = send("t7", "skip").json()  # t7 has no fix step, so this is a new sentence
    assert r["kind"] == "check"


def test_limit():
    r = send("t8", "limit")
    assert r.status_code == 429 and r.json()["error"] == "limit"


def test_one_call_each():
    before = calls()
    send("t10", "He go home.")
    assert calls() == before + 1
    send("t10", "He goes home.")  # a try in the fix step
    assert calls() == before + 2
    ask_maher("t10", "When do I use an?")
    assert calls() == before + 3
    send("t10", "She have a cat.")
    send("t10", "skip")  # skip needs no call
    assert calls() == before + 4


def test_ask_with_context():
    r = ask_maher("a1", 'Why is it "went" and not "goed"?',
                  {"sentence": "Yesterday I goed home.", "wrong": "goed", "correct": "went"})
    r = r.json()
    assert "go" in r["answer_ar"] and {"before": "go", "after": "went"} in r["examples"]
    assert r["practice"]


def test_ask_free_question():
    r = ask_maher("a2", "When do I use an?").json()
    assert "an" in r["answer_ar"] and r["examples"]


def test_ask_remembers_practice():
    r = ask_maher("a3", "Can you give me a quick test?").json()
    assert r["practice"]
    r = ask_maher("a3", "ate").json()  # an answer, Maher checks it
    checked = ("أحسنت", "ليس تمامًا")
    assert any(w in r["answer_ar"] for w in checked)
    # another thread has no practice question, so "ate" is just a question
    r = ask_maher("a4", "ate").json()
    assert not any(w in r["answer_ar"] for w in checked)


def test_ask_and_chat_memory_apart():
    send("a5", "I buyed a book.")  # chat is in the fix step now
    ask_maher("a5", "When do I use an?")
    r = send("a5", "I bought a book.").json()  # still the fix step
    assert r["kind"] == "retry" and r["status"] == "correct"


def test_ask_while_fixing():
    before = calls()
    r = ask_maher("a7", 'Can you help me fix "goed"?',
                  {"sentence": "Yesterday I goed home.", "wrong": "goed"})
    assert calls() == before + 1
    r = r.json()
    assert r["answer_ar"] and "went" not in r["answer_ar"]
    assert r["examples"] == [] and r["practice"] == ""


def practice(thread, wrong, correct, sentence=""):
    return client.post("/ask", json={
        "thread_id": thread, "question": "Practice", "practice": True,
        "context": {"sentence": sentence, "wrong": wrong, "correct": correct},
    })


def learned_now(thread):
    # the next chat answer has the mistakes list
    return {m["wrong"]: m["learned"] for m in send(thread, "Nice day.").json()["mistakes"]}


def test_practice_right_answer():
    send("p1", "She have a cat.")
    send("p1", "skip")  # not learned
    before = calls()
    r = practice("p1", "She have", "She has", "She have a cat.").json()
    assert r["practice"] and r["learned"] is None
    r = ask_maher("p1", "He has two brothers.").json()
    assert calls() == before + 2  # 1 per question, marking it needs no call
    assert r["passed"] and r["learned"] == "She have"
    assert {m["wrong"]: m["learned"] for m in r["mistakes"]} == {"She have": True}
    assert learned_now("p1") == {"She have": True}


def test_practice_wrong_answer():
    send("p2", "i went home.")
    send("p2", "skip")
    practice("p2", "i", "I", "i went home.")
    r = ask_maher("p2", "my brother and i are friends").json()
    assert not r["passed"] and r["learned"] is None
    assert r["practice"]  # the same test again, so you can try once more
    assert learned_now("p2") == {"i": False}
    r = ask_maher("p2", "My brother and I are friends.").json()
    assert r["passed"] and r["learned"] == "i"


def test_practice_other_thread():
    send("p3", "He go home.")
    send("p3", "skip")
    practice("p4", "He go", "He goes")
    ask_maher("p4", "My sister works in a bank.")
    assert learned_now("p3") == {"He go": False}


def test_follow_ups():
    first = ask_maher("f1", "When do I use an?").json()
    before = calls()
    r = ask_maher("f1", "Explain it simpler, please.").json()
    assert calls() == before + 1
    assert r["answer_ar"] != first["answer_ar"] and len(r["answer_ar"]) < len(first["answer_ar"])
    r = ask_maher("f1", "Give me more examples, please.").json()
    old = {(x["before"], x["after"]) for x in first["examples"]}
    new = {(x["before"], x["after"]) for x in r["examples"]}
    assert len(new) >= 3 and not (old & new)  # new ones, not the same again
    r = ask_maher("f1", "Test me.").json()
    assert r["practice"] and not r["passed"]  # "Test me." is not an answer


def test_buttons_follow_the_talk():
    r = ask_maher("b1", "When do I use an?").json()
    assert "Simpler please" in r["suggestions"]
    r = ask_maher("b1", "Test me.").json()
    assert r["practice"] and r["suggestions"] == ["Give me a hint", "Show me the answer"]
    r = ask_maher("b1", "a").json()  # wrong answer
    assert not r["passed"] and "Show me the answer" in r["suggestions"]
    r = ask_maher("b1", "Show me the answer").json()
    assert "an" in r["answer_ar"] and "I'm done, thanks" in r["suggestions"]
    r = ask_maher("b1", "Another one, please").json()
    assert r["practice"]


def test_right_answer_asks_another_or_done():
    ask_maher("b2", "When do I use an?")
    r = ask_maher("b2", "an").json()
    assert r["passed"] and r["suggestions"] == ["Another one, please", "I'm done, thanks"]


def test_practice_answer_whole_check():
    ask_maher("w1", "When do I use an?")  # practice: I ate ___ orange.
    r = ask_maher("w1", "an, and i like it").json()
    assert r["passed"] and "ملاحظة صغيرة" in r["answer_ar"] and "i ← I" in r["answer_ar"]
    # no slips, no note
    ask_maher("w2", "When do I use an?")
    r = ask_maher("w2", "an").json()
    assert r["passed"] and "ملاحظة" not in r["answer_ar"]


def test_ask_fields_required():
    # Gemini skips optional fields
    for model in (ask.AskResult, ask.Example):
        schema = model.model_json_schema()
        assert set(schema["required"]) == set(schema["properties"]), model.__name__


def test_ask_limit():
    r = ask_maher("a6", "limit")
    assert r.status_code == 429 and r.json()["error"] == "limit"


def test_empty():
    assert send("t9", "   ").status_code == 400
    assert send("t9", "").status_code == 422
    assert ask_maher("t9", "  ").status_code == 400


if __name__ == "__main__":
    tests = [f for name, f in list(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"\nall {len(tests)} tests passed")
