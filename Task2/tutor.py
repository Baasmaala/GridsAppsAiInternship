import os
import time
from typing import TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai.chat_models import GoogleAPIError
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

load_dotenv()


# --- the JSON the model gives back ---

class Mistake(BaseModel):
    wrong: str = Field(description="the wrong words, exactly as the user wrote them")
    correct: str = Field(description="the correct words")
    explanation_ar: str = Field(description="a short explanation in Arabic")
    # no defaults: Gemini skips optional fields
    reason_en: str = Field(description="a very short reason in simple English, max 6 words")


class CheckResult(BaseModel):
    has_errors: bool
    errors: list[Mistake]
    corrected: str = Field(description="the whole last message with all mistakes fixed")
    reply: str = Field(description="a short friendly answer in simple English")


class RetryResult(BaseModel):
    still_wrong: list[str] = Field(
        description='the "wrong" text of each mistake that is not fixed yet'
    )
    hint: str = Field(description="a small hint in Arabic, without the answer")
    new_errors: list[Mistake] = Field(
        description="every other mistake in the new try, not in the list"
    )
    corrected: str = Field(description="the whole new try with all mistakes fixed")


# --- the state the graph keeps between turns ---

class State(TypedDict):
    sentence: str   # what the user just wrote
    result: dict    # the JSON from check_grammar or check_retry
    mistakes: list  # all mistakes in this chat (+ learned, reminded)
    pending: dict   # the sentence we are fixing, empty = no fix step
    history: list   # last 4 messages, so the model knows the chat
    turn: int       # how many sentences so far (retries don't count)
    answer: str     # the text we print
    reminder: dict  # the old mistake reminded this turn, or None
    status: str     # fix step: correct, almost, gave_up, skipped (None = new sentence)


MAX_TRIES = 2


PROMPT = """You are Maher, a friendly English tutor for Arab learners.
Check ONLY the last message for grammar and spelling mistakes.
Older messages are just so you know what we talked about.

- has_errors: true if the last message has mistakes.
- errors: one item per mistake. explanation_ar must be in Arabic, short and simple.
  Use correct Modern Standard Arabic (say "غير المنتظم", not "الغير منتظم").
  reason_en: a very short reason in simple English, max 6 words
  (like "Past of go is irregular.").
- reply: 1-2 short sentences in simple English. Answer what the user said
  and keep the chat going (you can ask a question).
  If the last message has mistakes, be gentle and encouraging.
  If it has no mistakes, start with a short warm praise.
  React to what they said like a real person who is interested, and use
  words at their level.
  Don't list the corrections in reply, they are shown on their own.
- corrected: the whole last message with all mistakes fixed."""

RETRY_PROMPT = """You are Maher, a friendly English tutor for Arab learners.
The user made mistakes in a sentence and now wrote it again (the "new try").
Check the WHOLE new try like a careful teacher, word by word, not only the
old mistakes.

Fill ALL the fields:
- still_wrong: the "wrong" text of each mistake from the list that is NOT
  fixed in the new try, copied exactly from the list. Empty if all are fixed.
- new_errors: EVERY other mistake in the new try (tense, verb form, a/an,
  spelling, capital I, ...), for example in words the user added or changed.
  One item per mistake: wrong (exactly as written in the new try), correct,
  explanation_ar (short, correct Modern Standard Arabic), reason_en (max 6
  words). Don't repeat mistakes from the list. Empty only if the rest of the
  new try is really correct.
- corrected: the whole new try with every mistake fixed (old and new).
- hint: if a mistake from the list is still wrong, one short hint in Arabic,
  without the correct words. Use correct Modern Standard Arabic (say
  "غير المنتظم", not "الغير منتظم"). Empty if all of them are fixed."""

FAKE = os.getenv("FAKE_MODEL") == "1"

if FAKE:
    # no API requests, see fake_model.py
    from fake_model import FakeChecker, FakeRetryChecker
    checker = FakeChecker()
    retry_checker = FakeRetryChecker()
else:
    # max_retries=1 means only 1 try in total, so a 429 is never retried
    llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash", max_retries=1)
    checker = llm.with_structured_output(CheckResult)
    retry_checker = llm.with_structured_output(RetryResult)


def call_model(model, messages):
    # 503 = server busy, so wait and try again (3 tries max)
    # 429 is not caught here, main.py stops the chat
    for attempt in range(3):
        try:
            return model.invoke(messages)
        except GoogleAPIError as e:
            if e.code != 503 or attempt == 2:
                raise
            print("  (server is busy, waiting 5 seconds...)")
            time.sleep(5)


def key(text):
    # so "I goed", "i goed" and '"I goed"' are the same mistake
    return text.strip().strip('"').lower()


def add_history(state, answer):
    # keep only the last 4 messages
    history = state.get("history", []) + [
        {"role": "user", "text": state["sentence"]},
        {"role": "tutor", "text": answer},
    ]
    return history[-4:]


# --- nodes ---

def check_grammar(state: State):
    # 1 model call per sentence: check + reply together
    messages = [SystemMessage(PROMPT)]
    for msg in state.get("history", []):
        if msg["role"] == "user":
            messages.append(HumanMessage(msg["text"]))
        else:
            messages.append(AIMessage(msg["text"]))
    messages.append(HumanMessage(state["sentence"]))

    result = call_model(checker, messages)
    return {"result": result.model_dump()}


def add_mistakes(mistakes, errors, sentence):
    # add the new mistakes, skip the ones we already have
    mistakes = [dict(m) for m in mistakes]
    by_key = {key(m["wrong"]): m for m in mistakes}
    for e in errors:
        m = by_key.get(key(e["wrong"]))
        if m:
            m["learned"] = False  # made it again, so not learned anymore
        else:
            m = {**e, "learned": False, "reminded": 0, "sentence": sentence}
            mistakes.append(m)
            by_key[key(e["wrong"])] = m
    return mistakes


def remember(state: State):
    errors = state["result"]["errors"]
    return {"mistakes": add_mistakes(state.get("mistakes", []), errors, state["sentence"])}


def reply(state: State):
    # no model call here, just build the text
    result = state["result"]
    turn = state.get("turn", 0) + 1
    mistakes = [dict(m) for m in state.get("mistakes", [])]
    lines = [result["reply"]]

    for e in result["errors"]:
        lines.append(f'  "{e["wrong"]}" -> "{e["correct"]}"')
        lines.append(f"  {e['explanation_ar']}")

    # every 3rd sentence, remind one old mistake that is not learned yet
    # (not one from right now). Least reminded first, then the oldest,
    # so every mistake gets its turn.
    now = {key(e["wrong"]) for e in result["errors"]}
    old = [m for m in mistakes if not m["learned"] and key(m["wrong"]) not in now]
    reminder = None
    if old and turn % 3 == 0:
        m = min(old, key=lambda m: m["reminded"])
        m["reminded"] += 1
        reminder = {"wrong": m["wrong"], "correct": m["correct"]}
        lines.append(f'\nDon\'t forget: say "{m["correct"]}", not "{m["wrong"]}".')

    # mistakes -> start the fix step
    pending = {}
    if result["errors"]:
        pending = {
            "sentence": state["sentence"],
            "corrected": result["corrected"],
            "errors": result["errors"],
            "tries": 0,
        }
        lines.append("\nTry again: write your sentence correctly (or type 'skip').")

    answer = "\n".join(lines)
    return {
        "answer": answer,
        "history": add_history(state, answer),
        "turn": turn,
        "mistakes": mistakes,
        "pending": pending,
        "reminder": reminder,
        "status": None,
    }


def check_retry(state: State):
    # 1 model call: is the new try correct?
    p = state["pending"]
    errors = "\n".join(f'- "{e["wrong"]}" -> "{e["correct"]}"' for e in p["errors"])
    messages = [
        SystemMessage(RETRY_PROMPT),
        HumanMessage(
            f"First sentence: {p['sentence']}\n"
            f"Mistakes:\n{errors}\n"
            f"New try: {state['sentence']}"
        ),
    ]
    result = call_model(retry_checker, messages)
    return {"result": result.model_dump()}


def retry_reply(state: State):
    # no model call here, just build the text
    p = state["pending"]
    mistakes = [dict(m) for m in state.get("mistakes", [])]

    if key(state["sentence"]) == "skip":
        answer = f'OK, let\'s go on. The correct sentence is: "{p["corrected"]}"'
        return {
            "answer": answer,
            "history": add_history(state, answer),
            "pending": {},
            "reminder": None,
            "status": "skipped",
        }

    result = state["result"]
    still = {key(w) for w in result["still_wrong"]}
    left = [e for e in p["errors"] if key(e["wrong"]) in still]

    # the fixed ones are learned, so no more reminders about them
    old = {key(e["wrong"]) for e in p["errors"]}
    fixed = old - still
    for m in mistakes:
        if key(m["wrong"]) in fixed:
            m["learned"] = True

    # new mistakes in the new words
    new = [e for e in result.get("new_errors", []) if key(e["wrong"]) not in old]
    if new:
        mistakes = add_mistakes(mistakes, new, state["sentence"])
    corrected = result.get("corrected") or p["corrected"]

    tries = p["tries"] + 1
    pending = {}
    if not left and not new:
        status = "correct"
        answer = "Correct! Well done."
    elif not left:
        # old ones fixed, new ones found -> new fix step
        status = "fixed_new"
        lines = ["You fixed it! But there is a new small mistake:"]
        for e in new:
            lines.append(f'  "{e["wrong"]}" -> "{e["correct"]}"')
            lines.append(f"  {e['explanation_ar']}")
        lines.append("Try again (or type 'skip').")
        answer = "\n".join(lines)
        pending = {"sentence": state["sentence"], "corrected": corrected, "errors": new, "tries": 0}
    elif tries < MAX_TRIES:
        status = "almost"
        lines = [f"Almost! (try {tries} of {MAX_TRIES})"]
        if result["hint"]:
            lines.append(f"  {result['hint']}")
        lines.append("Try again (or type 'skip').")
        answer = "\n".join(lines)
        pending = {**p, "errors": left + new, "tries": tries, "corrected": corrected}
    else:
        status = "gave_up"
        answer = f'Good try! The correct sentence is: "{corrected}"'

    return {
        "answer": answer,
        "history": add_history(state, answer),
        "mistakes": mistakes,
        "pending": pending,
        "reminder": None,
        "status": status,
    }


def route_start(state: State):
    # fixing a mistake -> check the new try ('skip' needs no model call)
    if state.get("pending"):
        return "retry_reply" if key(state["sentence"]) == "skip" else "check_retry"
    return "check_grammar"


def route(state: State):
    # mistakes -> remember them first, no mistakes -> reply
    return "remember" if state["result"]["has_errors"] else "reply"


# --- the graph ---

def build_graph():
    graph = StateGraph(State)
    graph.add_node("check_grammar", check_grammar)
    graph.add_node("remember", remember)
    graph.add_node("reply", reply)
    graph.add_node("check_retry", check_retry)
    graph.add_node("retry_reply", retry_reply)

    graph.add_conditional_edges(
        START, route_start, ["check_grammar", "check_retry", "retry_reply"]
    )
    graph.add_conditional_edges("check_grammar", route, ["remember", "reply"])
    graph.add_edge("remember", "reply")
    graph.add_edge("reply", END)
    graph.add_edge("check_retry", "retry_reply")
    graph.add_edge("retry_reply", END)

    # MemorySaver keeps the state between turns (only while the app runs)
    return graph.compile(checkpointer=MemorySaver())
