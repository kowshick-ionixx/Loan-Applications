from approval_graph import SERDE, build_graph
from langgraph.checkpoint.memory import InMemorySaver

graph = build_graph(InMemorySaver(serde=SERDE))

customer_id = input("Customer ID : ").strip()
email = input("Loan request: ").strip()

inputs = {"customer_id": customer_id, "email": email, "log": []}
config = {"configurable": {"thread_id": f"case-{customer_id}"}}


def show(title: str, config: dict) -> None:
    """Print the decision and the full log saved for one thread."""
    snapshot = graph.get_state(config)
    values = snapshot.values
    print(f"\n{title}")
    print(f"  decision: {values.get('decision')}")
    print(f"  reason  : {values.get('reason')}")
    if snapshot.next:
        print(f"  waiting at: {snapshot.next} (refer cases pause; see Lab 2)")
    print(f"  log ({len(values.get('log', []))} lines):")
    for line in values.get("log", []):
        print(f"    {line}")


graph.invoke(inputs, config)
show(f"Run 1 on case-{customer_id}", config)

graph.invoke(inputs, config)
show(f"Run 2 on case-{customer_id} (same thread)", config)

other = {"configurable": {"thread_id": "case-new"}}
print("\ncase-new before any run:", graph.get_state(other).values)

print(f"\nHistory of case-{customer_id} (newest first):")
for snapshot in graph.get_state_history(config):
    print(f"  step {snapshot.metadata['step']:>2}  next={snapshot.next}")
