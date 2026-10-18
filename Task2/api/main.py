# API for the site: /chat = tutor, /ask = Ask Maher (1 model call each)
# Run from Task2: uv run uvicorn api.main:app --reload

import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from langchain_google_genai.chat_models import (
    ChatGoogleGenerativeAIError,
    GoogleAPIError,
    GoogleRateLimitError,
)
from pydantic import BaseModel, Field

from ask import build_ask_graph
from tutor import FAKE, MAX_TRIES, build_graph, key

app = FastAPI(title="Maher")

# thread_id keeps each chat apart, 2 graphs = 2 memories
graph = build_graph()
ask_graph = build_ask_graph()


class ChatIn(BaseModel):
    thread_id: str = Field(min_length=1, max_length=100)
    sentence: str = Field(min_length=1, max_length=500)


class Context(BaseModel):
    # the mistake from the chat
    # no correct = still fixing, Maher must not give the answer
    sentence: str = Field(default="", max_length=500)
    wrong: str = Field(max_length=200)
    correct: str = Field(default="", max_length=200)


class AskIn(BaseModel):
    thread_id: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=1, max_length=500)
    context: Context | None = None
    # Practice it (My mistakes)
    practice: bool = False


def error(code, kind, message):
    return JSONResponse(status_code=code, content={"error": kind, "message": message})


def run(g, data, thread_id):
    # -> (state, None) or (None, error)
    if not FAKE and not os.getenv("GOOGLE_API_KEY"):
        return None, error(500, "no_key", "No GOOGLE_API_KEY found in .env.")
    try:
        return g.invoke(data, {"configurable": {"thread_id": thread_id}}), None
    except GoogleRateLimitError:
        return None, error(429, "limit", "Daily limit reached.")
    except GoogleAPIError as e:
        # still failing after the retries in tutor.py
        return None, error(503, "busy", f"Server problem ({e.code}).")
    except ChatGoogleGenerativeAIError as e:
        # wrong key, wrong model name, ...
        return None, error(500, "model", str(e))


@app.get("/health")
def health():
    return {"ok": True, "fake_model": FAKE}


@app.post("/chat")
def chat(body: ChatIn):
    sentence = body.sentence.strip()
    if not sentence:
        return error(400, "empty", "Write a sentence first.")

    config = {"configurable": {"thread_id": body.thread_id}}
    # need the old fix step for the correct sentence (it is empty after)
    before = graph.get_state(config).values.get("pending") or {}

    state, err = run(graph, {"sentence": sentence}, body.thread_id)
    if err:
        return err

    pending = state.get("pending") or {}
    fixing = {"tries": pending["tries"], "max_tries": MAX_TRIES} if pending else None
    status = state.get("status")
    # for My mistakes
    mistakes = state.get("mistakes", [])

    if status is None:
        result = state["result"]
        return {
            "kind": "check",
            "sentence": sentence,
            "reply": result["reply"],
            "errors": result["errors"],
            "corrected": result["corrected"],
            "reminder": state.get("reminder"),
            "fixing": fixing,
            "mistakes": mistakes,
        }

    # fix step: no correct words when "almost", only the hint
    result = state["result"]
    corrected = ""
    if status == "skipped":
        corrected = before.get("corrected", "")
    elif status in ("gave_up", "fixed_new"):
        corrected = result.get("corrected") or before.get("corrected", "")
    return {
        "kind": "retry",
        "sentence": sentence,
        "status": status,
        "hint": result.get("hint", "") if status == "almost" else "",
        # never the right words here
        "still_wrong": [e["wrong"] for e in pending.get("errors", [])] if status == "almost" else [],
        "errors": pending.get("errors", []) if status == "fixed_new" else [],
        "corrected": corrected,
        "fixing": fixing,
        "mistakes": mistakes,
    }


@app.post("/ask")
def ask(body: AskIn):
    question = body.question.strip()
    if not question:
        return error(400, "empty", "Write a question first.")

    c = body.context
    data = {}
    if body.practice and c:
        data["practice_for"] = c.wrong
        question = (
            f'From my chat: I wrote "{c.sentence}". '
            f'The mistake: "{c.wrong}" -> "{c.correct}". '
            "Give me one short practice sentence for this mistake. Do not give the answer."
        )
    elif c and c.correct:
        question = (
            f'From my chat: I wrote "{c.sentence}". '
            f'The mistake: "{c.wrong}" -> "{c.correct}". {question}'
        )
    elif c:
        question = (
            f'From my chat: I am fixing my sentence "{c.sentence}". '
            f'The mistake is in "{c.wrong}". Help me, but do not tell me the answer. {question}'
        )

    state, err = run(ask_graph, {**data, "question": question}, body.thread_id)
    if err:
        return err

    result = state["result"]
    learned, mistakes = None, None
    target = state.get("practice_for")
    if result.get("passed") and target:
        # passed: learned in the chat memory too (no model call)
        config = {"configurable": {"thread_id": body.thread_id}}
        mistakes = [dict(m) for m in graph.get_state(config).values.get("mistakes", [])]
        for m in mistakes:
            if key(m["wrong"]) == key(target):
                m["learned"] = True
                learned = m["wrong"]
        if learned:
            graph.update_state(config, {"mistakes": mistakes})
        ask_graph.update_state(config, {"practice_for": ""})
    return {**result, "learned": learned, "mistakes": mistakes if learned else None}
