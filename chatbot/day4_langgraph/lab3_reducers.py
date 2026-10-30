import operator
from typing import Annotated, TypedDict

from langgraph.graph import StateGraph, START, END


class State(TypedDict):
    text: str
    log: Annotated[list[str], operator.add]


def shout(state: State):
    return {"text": state["text"].upper(), "log": ["shout ran"]}


def exclaim(state: State):
    return {"text": state["text"] + "!", "log": ["exclaim ran"]}


builder = StateGraph(State)
builder.add_node("shout", shout)
builder.add_node("exclaim", exclaim)
builder.add_edge(START, "shout")
builder.add_edge("shout", "exclaim")
builder.add_edge("exclaim", END)
graph = builder.compile()

print(graph.invoke({"text": "hello", "log": []}))
