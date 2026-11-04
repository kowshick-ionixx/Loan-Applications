from approval_graph import sqlite_graph
from langgraph.types import Command

graph = sqlite_graph()


def case_config(customer_id: str) -> dict:
    """The thread config for one customer's case."""
    return {"configurable": {"thread_id": f"case-{customer_id}"}}


def waiting_cases() -> list[str]:
    """Thread IDs of every saved case that is paused for an officer."""
    thread_ids = {
        saved.config["configurable"]["thread_id"]
        for saved in graph.checkpointer.list(None)
    }
    return sorted(
        thread_id
        for thread_id in thread_ids
        if graph.get_state({"configurable": {"thread_id": thread_id}}).interrupts
    )


def show_result(config: dict) -> None:
    """Print the decision, or that the case is waiting for an officer."""
    snapshot = graph.get_state(config)
    if snapshot.interrupts:
        print(f"  Waiting for an officer: {snapshot.interrupts[0].value['reason']}")
        return
    print(f"  Decision: {snapshot.values['decision'].upper()}")
    print(f"  Reason  : {snapshot.values['reason']}")


def start() -> None:
    customer_id = input("Customer ID : ").strip()
    config = case_config(customer_id)
    if graph.get_state(config).interrupts:
        print("  This case is already waiting for a decision. Choose 3 to decide it.")
        return
    email = input("Loan request: ").strip()
    if not customer_id or not email:
        print("  Please enter both a customer ID and the loan request.")
        return
    graph.invoke({"customer_id": customer_id, "email": email, "log": []}, config)
    show_result(config)


def pending() -> None:
    cases = waiting_cases()
    if not cases:
        print("  No cases are waiting for a decision.")
        return
    for thread_id in cases:
        snapshot = graph.get_state({"configurable": {"thread_id": thread_id}})
        question = snapshot.interrupts[0].value
        print(f"  {thread_id}: customer {question['customer']}, {question['reason']}")


def decide() -> None:
    customer_id = input("Customer ID : ").strip()
    config = case_config(customer_id)
    snapshot = graph.get_state(config)
    if not snapshot.interrupts:
        print("  This case is not waiting for a decision.")
        return
    question = snapshot.interrupts[0].value
    print(f"  {question['question']} {question['reason']}")
    decision = ""
    while decision not in ("approve", "reject"):
        decision = input("  Decision (approve/reject): ").strip().lower()
    graph.invoke(Command(resume={"decision": decision}), config)
    show_result(config)


ACTIONS = {"1": start, "2": pending, "3": decide}


def main() -> None:
    print("Loan Officer App. Cases are saved in checkpoints.db and survive a restart.")
    while True:
        print("\n1) Start a case   2) Pending cases   3) Decide a case   4) Exit")
        try:
            choice = input("Choose: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break
        if choice in ("4", "exit", "quit"):
            break
        action = ACTIONS.get(choice)
        if action is None:
            print("  Please choose 1, 2, 3 or 4.")
            continue
        try:
            action()
        except (EOFError, KeyboardInterrupt):
            break
        except Exception as exc:  # noqa: BLE001
            print(f"  Sorry, something went wrong ({exc}). Please try again.")
    print("Bye.")


if __name__ == "__main__":
    main()
