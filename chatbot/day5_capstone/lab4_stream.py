from approval_graph import sqlite_graph
from langgraph.types import Command

graph = sqlite_graph()


def narrate(stream) -> bool:
    """Print each step as it finishes. Returns True if the graph paused."""
    paused = False
    for step in stream:
        for node, update in step.items():
            if node == "__interrupt__":
                question = update[0].value
                print(f"  [PAUSED]   {question['question']} ({question['reason']})")
                paused = True
            else:
                label = f"[{node}]"
                print(f"  {label:<10} {update['log'][-1]}")
    return paused


customer_id = input("Customer ID : ").strip()
config = {"configurable": {"thread_id": f"case-{customer_id}"}}

if graph.get_state(config).next:
    print("  This case is already waiting for a decision.")
    print("  Decide it with: uv run python day5_capstone/lab3_sqlite.py resume")
else:
    email = input("Loan request: ").strip()
    inputs = {"customer_id": customer_id, "email": email, "log": []}

    print(f"\nStreaming case-{customer_id}")
    paused = narrate(graph.stream(inputs, config, stream_mode="updates"))

    if paused:
        decision = ""
        while decision not in ("approve", "reject"):
            decision = input("\nManager decision (approve/reject): ").strip().lower()
        print("\nStreaming the resume")
        resume = Command(resume={"decision": decision})
        narrate(graph.stream(resume, config, stream_mode="updates"))
