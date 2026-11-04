import sys

from approval_graph import sqlite_graph
from langgraph.types import Command

graph = sqlite_graph()


def ask_case() -> tuple[str, dict]:
    """Ask for a customer ID and return it with that case's thread config."""
    customer_id = input("Customer ID : ").strip()
    return customer_id, {"configurable": {"thread_id": f"case-{customer_id}"}}


def show(snapshot) -> None:
    """Print where a saved case is: waiting for a decision, or finished."""
    values = snapshot.values
    if snapshot.interrupts:
        question = snapshot.interrupts[0].value
        print(f"  waiting at: {snapshot.next}")
        print(f"  question  : {question['question']}")
        print(f"  reason    : {question['reason']}")
    else:
        print(f"  decision: {values.get('decision')}")
        print(f"  reason  : {values.get('reason')}")
    print("  log:")
    for line in values.get("log", []):
        print(f"    {line}")


def start() -> None:
    customer_id, config = ask_case()
    if graph.get_state(config).next:
        print("  This case is already waiting for a decision. Run resume.")
        return
    email = input("Loan request: ").strip()
    graph.invoke({"customer_id": customer_id, "email": email, "log": []}, config)
    snapshot = graph.get_state(config)
    show(snapshot)
    if snapshot.interrupts:
        print("\nSaved to checkpoints.db. Close Python, then run:")
        print("  uv run python day5_capstone/lab3_sqlite.py resume")


def status() -> None:
    _, config = ask_case()
    snapshot = graph.get_state(config)
    if not snapshot.values:
        print("  No saved case for this customer.")
        return
    show(snapshot)


def resume() -> None:
    _, config = ask_case()
    snapshot = graph.get_state(config)
    if not snapshot.interrupts:
        print("  This case is not waiting for a decision.")
        return
    show(snapshot)
    decision = ""
    while decision not in ("approve", "reject"):
        decision = input("\nManager decision (approve/reject): ").strip().lower()
    graph.invoke(Command(resume={"decision": decision}), config)
    print("\nAfter resume")
    show(graph.get_state(config))


MODES = {"start": start, "status": status, "resume": resume}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in MODES:
        print("Usage: uv run python day5_capstone/lab3_sqlite.py start|status|resume")
        sys.exit(1)
    MODES[sys.argv[1]]()
