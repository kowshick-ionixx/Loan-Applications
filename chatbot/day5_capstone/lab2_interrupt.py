from approval_graph import SERDE, build_graph
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

graph = build_graph(InMemorySaver(serde=SERDE))

customer_id = input("Customer ID : ").strip()
email = input("Loan request: ").strip()

inputs = {"customer_id": customer_id, "email": email, "log": []}
config = {"configurable": {"thread_id": f"case-{customer_id}"}}

print("\nFirst call")
result = graph.invoke(inputs, config)

if "__interrupt__" in result:
    question = result["__interrupt__"][0].value
    print(f"  paused, question: {question['question']}")
    print(f"  customer: {question['customer']}")
    print(f"  reason  : {question['reason']}")
    print(f"  waiting at: {graph.get_state(config).next}")

    decision = ""
    while decision not in ("approve", "reject"):
        decision = input("\nManager decision (approve/reject): ").strip().lower()

    print("\nSecond call (manager answers)")
    result = graph.invoke(Command(resume={"decision": decision}), config)
else:
    print("  no pause: the graph decided on its own")

print(f"  decision: {result['decision']}")
print(f"  reason  : {result['reason']}")
print("  log:")
for line in result["log"]:
    print(f"    {line}")
