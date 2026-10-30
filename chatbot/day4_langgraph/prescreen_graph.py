import sys

from langgraph.graph import StateGraph, START, END

from state import LoanState
from nodes import (
    approve,
    intake,
    need_info,
    refer,
    refer_reasons,
    reject,
    score,
    validate,
)


def after_validate(state: LoanState):
    """Rule 1: amount or tenure missing or not above 0, or customer not found -> need_info."""
    if state["problems"]:
        return "need_info"
    return "score"


def route(state: LoanState):
    """Rules 2 to 4, in priority order: reject, then refer, then approve."""
    if state["failed_rules"]:
        return "reject"
    if refer_reasons(state):
        return "refer"
    return "approve"


builder = StateGraph(LoanState)
builder.add_node("intake", intake)
builder.add_node("validate", validate)
builder.add_node("score", score)
builder.add_node("approve", approve)
builder.add_node("refer", refer)
builder.add_node("reject", reject)
builder.add_node("need_info", need_info)

builder.add_edge(START, "intake")
builder.add_edge("intake", "validate")
builder.add_conditional_edges(
    "validate", after_validate, {"score": "score", "need_info": "need_info"}
)
builder.add_conditional_edges(
    "score", route, {"approve": "approve", "refer": "refer", "reject": "reject"}
)
for outcome in ("approve", "refer", "reject", "need_info"):
    builder.add_edge(outcome, END)

graph = builder.compile()


def prescreen(customer_id: str, email: str) -> dict:
    """Run one application through the graph, printing each step as it happens."""
    state = {"customer_id": customer_id, "email": email, "log": []}
    for step in graph.stream(state, stream_mode="updates"):
        for update in step.values():
            print(f"  {update['log'][-1]}")
            state |= update
    return state


def chat() -> None:
    """Type a customer ID and an enquiry; the graph pre-screens it. Type exit to quit."""
    print("Loan Pre-Screening. Type 'exit' to quit.")
    print("Loan request: what the customer wants, e.g. 'I need 5 lakh for 3 years for my house'")
    while True:
        try:
            customer_id = input("\nCustomer ID  : ").strip()
            if customer_id.lower() in ("exit", "quit"):
                break
            email = input("Loan request: ").strip()
            if email.lower() in ("exit", "quit"):
                break
        except (EOFError, KeyboardInterrupt):
            break
        if not customer_id or not email:
            print("  Please enter both a customer ID and the enquiry text.")
            continue

        try:
            result = prescreen(customer_id, email)
        except Exception as exc:  # noqa: BLE001
            print(f"  Sorry, something went wrong ({exc}). Please try again.")
            continue
        print(f"\nDecision : {result['decision'].upper()}")
        print(f"Reason   : {result['reason']}")
    print("Bye.")


if __name__ == "__main__":
    if "--diagram" in sys.argv:
        print(graph.get_graph().draw_mermaid())
    else:
        chat()
