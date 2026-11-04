from datetime import datetime

import approval_graph  # noqa: F401  puts day4_langgraph on the path for nodes
from accounts import UserContext, can_see_customer
from langgraph.types import Command
from nodes import RATE_PERCENT  # noqa: F401  re-exported for the decision card

DECISIONS = ("approve", "reject")


def thread_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def new_thread_id(now: datetime | None = None) -> str:
    """An ID like case-20261103-141502."""
    return f"case-{(now or datetime.now().astimezone()):%Y%m%d-%H%M%S}"


def case_values(graph, thread_id: str) -> dict:
    """The saved state of one case, or {} if there is no such case."""
    return graph.get_state(thread_config(thread_id)).values


def can_view(user: UserContext, values: dict) -> bool:
    """A case is visible to managers, and to the customer it belongs to."""
    return bool(values) and can_see_customer(user, values.get("customer_id", ""))


def all_thread_ids(graph) -> set[str]:
    return {
        saved.config["configurable"]["thread_id"]
        for saved in graph.checkpointer.list(None)
    }


def is_waiting(graph, thread_id: str) -> bool:
    return bool(graph.get_state(thread_config(thread_id)).interrupts)


def waiting_cases(graph) -> list[str]:
    """Thread IDs of every saved case paused for an officer, oldest ID first."""
    return sorted(t for t in all_thread_ids(graph) if is_waiting(graph, t))


def visible_cases(graph, user: UserContext) -> list[str]:
    """Every saved case this user may open."""
    return sorted(
        t for t in all_thread_ids(graph) if can_view(user, case_values(graph, t))
    )


def stream_case(graph, thread_id: str, customer_id: str, email: str):
    """Run a new application, yielding (node, update) as each step finishes.
    A pause is yielded as ("__interrupt__", question payload)."""
    inputs = {"customer_id": customer_id.strip(), "email": email, "log": []}
    for step in graph.stream(inputs, thread_config(thread_id), stream_mode="updates"):
        for node, update in step.items():
            if node == "__interrupt__":
                yield node, update[0].value
            else:
                yield node, update


def waiting_summary(graph, thread_id: str) -> dict:
    """What an officer needs to decide one paused case."""
    snapshot = graph.get_state(thread_config(thread_id))
    values = snapshot.values
    question = snapshot.interrupts[0].value
    enquiry = values.get("enquiry")
    customer = values.get("customer") or {}
    return {
        "thread_id": thread_id,
        "customer_id": values.get("customer_id"),
        "name": customer.get("name"),
        "amount": enquiry.amount if enquiry else None,
        "tenure_months": enquiry.tenure_months if enquiry else None,
        "emi": values.get("emi"),
        "reason": question["reason"],
        "question": question["question"],
    }


def decide(
    graph, thread_id: str, decision: str, officer: str, comment: str = ""
) -> dict:
    """Resume a paused case with an officer's decision. Returns the final state."""
    if decision not in DECISIONS:
        raise ValueError(f"decision must be one of {DECISIONS}")
    if not is_waiting(graph, thread_id):
        raise ValueError(f"{thread_id} is not waiting for a decision")
    resume = {"decision": decision, "comment": comment, "officer": officer}
    graph.invoke(Command(resume=resume), thread_config(thread_id))
    return case_values(graph, thread_id)


def history_rows(graph, thread_id: str) -> list[dict]:
    """One row per saved checkpoint, oldest first: the step, the node that
    produced it, what runs next, and the decision at that point."""
    snapshots = list(graph.get_state_history(thread_config(thread_id)))[::-1]
    rows, ran = [], "input"
    for snapshot in snapshots:
        rows.append(
            {
                "step": snapshot.metadata.get("step"),
                "node": ran,
                "next": ", ".join(snapshot.next) or "-",
                "decision": snapshot.values.get("decision") or "-",
            }
        )
        ran = ", ".join(snapshot.next) or "-"
    return rows
