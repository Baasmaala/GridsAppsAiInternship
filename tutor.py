import random
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


class CheckResult(BaseModel):
    has_errors: bool
    errors: list[Mistake]
    reply: str = Field(description="a short friendly answer in simple English")


# --- the state the graph keeps between turns ---

class State(TypedDict):
    sentence: str   # what the user just wrote
    result: dict    # the JSON from check_grammar
    mistakes: list  # all mistakes in this chat
    history: list   # last 4 messages, so the model knows the chat
    turn: int       # how many sentences so far
    answer: str     # the text we print


PROMPT = """You are a friendly English tutor for Arab learners.
Check ONLY the last message for grammar and spelling mistakes.
Older messages are just so you know what we talked about.

- has_errors: true if the last message has mistakes.
- errors: one item per mistake. explanation_ar must be in Arabic, short and simple.
- reply: 1-2 short sentences in simple English. Answer what the user said
  and keep the chat going (you can ask a question).
  Don't list the corrections in reply, they are shown on their own."""

# max_retries=1 means no retries (0 means "use the default" in the Google SDK)
llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash", max_retries=1)
checker = llm.with_structured_output(CheckResult)


def call_model(messages):
    # 503 = server busy, so wait and try again (3 tries max)
    # 429 is not caught here, main.py stops the chat
    for attempt in range(3):
        try:
            return checker.invoke(messages)
        except GoogleAPIError as e:
            if e.code != 503 or attempt == 2:
                raise
            print("  (server is busy, waiting 5 seconds...)")
            time.sleep(5)


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

    result = call_model(messages)
    return {"result": result.model_dump()}


def remember(state: State):
    # add only the new mistakes, skip the ones we already have
    mistakes = list(state.get("mistakes", []))
    known = {m["wrong"].lower() for m in mistakes}
    for e in state["result"]["errors"]:
        if e["wrong"].lower() not in known:
            mistakes.append(e)
            known.add(e["wrong"].lower())
    return {"mistakes": mistakes}


def reply(state: State):
    # no model call here, just build the text
    result = state["result"]
    turn = state.get("turn", 0) + 1
    lines = [result["reply"]]

    for e in result["errors"]:
        lines.append(f'  "{e["wrong"]}" -> "{e["correct"]}"')
        lines.append(f"  {e['explanation_ar']}")

    # every 3rd sentence, remind one old mistake (not one from right now)
    now = {e["wrong"].lower() for e in result["errors"]}
    old = [m for m in state.get("mistakes", []) if m["wrong"].lower() not in now]
    if old and turn % 3 == 0:
        m = random.choice(old)
        lines.append(f'\nDon\'t forget: say "{m["correct"]}", not "{m["wrong"]}".')

    answer = "\n".join(lines)

    # keep only the last 4 messages
    history = state.get("history", []) + [
        {"role": "user", "text": state["sentence"]},
        {"role": "tutor", "text": answer},
    ]
    return {"answer": answer, "history": history[-4:], "turn": turn}


def route(state: State):
    # mistakes -> remember them first, no mistakes -> reply
    return "remember" if state["result"]["has_errors"] else "reply"


# --- the graph ---

def build_graph():
    graph = StateGraph(State)
    graph.add_node("check_grammar", check_grammar)
    graph.add_node("remember", remember)
    graph.add_node("reply", reply)

    graph.add_edge(START, "check_grammar")
    graph.add_conditional_edges("check_grammar", route, ["remember", "reply"])
    graph.add_edge("remember", "reply")
    graph.add_edge("reply", END)

    # MemorySaver keeps the state between turns (only while the app runs)
    return graph.compile(checkpointer=MemorySaver())
