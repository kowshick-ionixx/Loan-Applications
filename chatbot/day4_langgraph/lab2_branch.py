from typing import TypedDict

from langgraph.graph import StateGraph, START, END


class State(TypedDict):
    text: str
    reply: str


def check(state: State):
    return {"text": state["text"].strip()}


def pick_path(state: State):
    if len(state["text"]) < 20:
        return "short"
    return "long"


def short_reply(state: State):
    return {"reply": "Short message, quick answer."}


def long_reply(state: State):
    return {"reply": "Long message, needs a detailed answer."}


builder = StateGraph(State)
builder.add_node("check", check)
builder.add_node("short_reply", short_reply)
builder.add_node("long_reply", long_reply)
builder.add_edge(START, "check")
builder.add_conditional_edges(
    "check", pick_path, {"short": "short_reply", "long": "long_reply"}
)
builder.add_edge("short_reply", END)
builder.add_edge("long_reply", END)
graph = builder.compile()

for text in ["Need a loan", "I need a loan of 5 lakh rupees for 3 years to renovate my house"]:
    print(f"\nInput: {text!r}")
    for step in graph.stream({"text": text}, stream_mode="updates"):
        print(step)
