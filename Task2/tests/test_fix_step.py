# Tests for the fix step and the reminder, with a fake model.
# No API key and no requests needed. Run: uv run python tests/test_fix_step.py

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault("GOOGLE_API_KEY", "fake")  # never used, the model is fake

import tutor
from tutor import CheckResult, Mistake, RetryResult


class Fake:
    # gives back the answers in order and counts the calls
    def __init__(self, answers):
        self.answers = list(answers)
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        return self.answers.pop(0)


goed = Mistake(wrong="I goed", correct="I went", explanation_ar="ماضي go هو went",
               reason_en="Past of go is irregular.")
buyed = Mistake(wrong="buyed", correct="bought", explanation_ar="ماضي buy هو bought",
                reason_en="Past of buy is irregular.")


def retry(**fields):
    return RetryResult(new_errors=[], corrected="", **fields)


def wrong(mistake, corrected):
    return CheckResult(has_errors=True, errors=[mistake], corrected=corrected, reply="Nice!")


def ok():
    return CheckResult(has_errors=False, errors=[], corrected="", reply="Great.")


def start(checks, retries):
    tutor.checker = Fake(checks)
    tutor.retry_checker = Fake(retries)
    graph = tutor.build_graph()
    config = {"configurable": {"thread_id": "test"}}

    def send(sentence):
        before = tutor.checker.calls + tutor.retry_checker.calls
        state = graph.invoke({"sentence": sentence}, config)
        state["calls"] = tutor.checker.calls + tutor.retry_checker.calls - before
        return state

    return send


def learned(state):
    return {m["wrong"]: m["learned"] for m in state["mistakes"]}


def test_fixed_on_second_try():
    send = start(
        [wrong(goed, "Yesterday I went to school.")],
        [retry(still_wrong=["I goed"], hint="فكر في الماضي"),
         retry(still_wrong=[], hint="")],
    )
    s = send("Yesterday I goed to school.")
    assert "Try again" in s["answer"] and s["calls"] == 1

    s = send("Yesterday I go to school.")
    assert "try 1 of 2" in s["answer"] and "فكر في الماضي" in s["answer"]
    assert s["calls"] == 1 and s["pending"]

    s = send("Yesterday I went to school.")
    assert "Correct!" in s["answer"] and s["calls"] == 1
    assert learned(s) == {"I goed": True} and not s["pending"]
    assert s["turn"] == 1  # retries don't count as turns


def test_wrong_two_times():
    send = start(
        [wrong(goed, "Yesterday I went to school.")],
        [retry(still_wrong=["I goed"], hint="h1"),
         retry(still_wrong=["I goed"], hint="h2")],
    )
    send("Yesterday I goed to school.")
    send("Yesterday I go to school.")
    s = send("Yesterday I goes to school.")
    assert '"Yesterday I went to school."' in s["answer"]
    assert learned(s) == {"I goed": False} and not s["pending"]


def test_skip_needs_no_model_call():
    send = start([wrong(buyed, "I bought a book.")], [])
    send("I buyed a book.")
    s = send("skip")
    assert s["calls"] == 0 and '"I bought a book."' in s["answer"]
    assert learned(s) == {"buyed": False} and not s["pending"]


def test_reminder_skips_learned():
    send = start(
        [wrong(goed, "I went."), wrong(buyed, "I bought it."), ok()],
        [retry(still_wrong=[], hint="")],
    )
    send("I goed.")
    send("I went.")  # fixed -> learned
    send("I buyed it.")
    send("skip")
    s = send("I like it.")  # turn 3
    assert 'not "buyed"' in s["answer"] and "goed" not in s["answer"]


def test_reminder_takes_turns():
    send = start(
        [wrong(goed, "I went."), wrong(buyed, "I bought it.")] + [ok() for _ in range(7)],
        [],
    )
    send("I goed.")
    send("skip")
    send("I buyed it.")
    send("skip")
    reminders = []
    for i in range(7):  # turns 3 to 9
        s = send(f"sentence {i}")
        if "Don't forget" in s["answer"]:
            reminders.append(s["answer"].split('not "')[1].rstrip('".'))
    assert reminders == ["I goed", "buyed", "I goed"]


def test_learned_mistake_made_again():
    send = start(
        [wrong(goed, "I went."), wrong(goed, "I went home.")],
        [retry(still_wrong=[], hint="")],
    )
    send("I goed.")
    s = send("I went.")
    assert learned(s) == {"I goed": True}
    s = send("I goed home.")
    assert learned(s) == {"I goed": False}


def test_model_fields_required():
    # Gemini skips optional fields
    for model in (Mistake, CheckResult, RetryResult):
        schema = model.model_json_schema()
        assert set(schema["required"]) == set(schema["properties"]), model.__name__


if __name__ == "__main__":
    tests = [f for name, f in list(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"\nall {len(tests)} tests passed")
