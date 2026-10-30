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

print(graph.get_graph().draw_mermaid())
