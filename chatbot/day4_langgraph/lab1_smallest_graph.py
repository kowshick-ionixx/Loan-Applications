from typing import TypedDict

from langgraph.graph import StateGraph, START, END


class State(TypedDict):
    text: str


def shout(state: State):
    return {"text": state["text"].upper()}


def exclaim(state: State):
    return {"text": state["text"] + "!"}


builder = StateGraph(State)
builder.add_node("shout", shout)
builder.add_node("exclaim", exclaim)
builder.add_edge(START, "shout")
builder.add_edge("shout", "exclaim")
builder.add_edge("exclaim", END)
graph = builder.compile()

print(graph.invoke({"text": "hello"}))