import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "day2_agents"))

from langchain.agents import create_agent
from langchain.messages import AIMessage, HumanMessage, ToolMessage
from loan_agent import SYSTEM_PROMPT, get_customer, model
from policy_tools import search_policy
from tools import check_eligibility, emi_calculator

COMBINED_PROMPT = SYSTEM_PROMPT + (
    "\n- For questions about loan policy (fees, rules, documents, disbursal), use "
    "search_policy and answer only from what it returns. Cite the section number, like (3.2)."
)


agent = create_agent(
    model,
    tools=[get_customer, emi_calculator, check_eligibility, search_policy],
    system_prompt=COMBINED_PROMPT,
)


def chat() -> None:
    """Type your own questions. The agent remembers the conversation until you type exit."""
    print("Loan Assistant (Day 2 tools + policy search). Type 'exit' to quit.")
    history = []

    while True:
        question = input("\nYou   : ").strip()

        if question.lower() in ("exit", "quit"):
            break
        if not question:
            continue

        history.append(HumanMessage(question))
        start = len(history)

        try:
            history = agent.invoke({"messages": history})["messages"]
        except Exception as exc:
            print(f"Agent : Sorry, something went wrong ({exc}). Please try again.")
            history.pop()
            continue

        for m in history[start:]:
            if isinstance(m, AIMessage) and m.tool_calls:
                for c in m.tool_calls:
                    print(f"  -> tool call  : {c['name']}({c['args']})")
            elif isinstance(m, ToolMessage):
                print(f"  <- tool result: {m.content}")

        print(f"Agent : {history[-1].content.strip()}")

    print("Bye.")


if __name__ == "__main__":
    chat()
