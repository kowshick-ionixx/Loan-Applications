import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.messages import AIMessage, HumanMessage, ToolMessage

sys.path.append(str(Path(__file__).resolve().parent.parent / "day2_agents"))

from policy_tools import search_policy
from tools import emi_calculator

load_dotenv()
model = init_chat_model("ollama:qwen3.5:9b", reasoning=False, temperature=0)

SYSTEM_PROMPT = (
    "You are a careful loan assistant at an Indian bank. Amounts are in rupees.\n"
    "- For questions about loan rules, fees or documents, use search_policy and "
    "answer only from what it returns. Cite the section number, like (3.2).\n"
    "- For EMI calculations, use emi_calculator. Never calculate numbers yourself.\n"
    "- If the policy does not cover something, say: I could not find this in the policy.\n"
    "- Keep answers short."
)

agent = create_agent(
    model,
    tools=[search_policy, emi_calculator],
    system_prompt=SYSTEM_PROMPT,
)


def label(msg) -> str:
    """Name each message by who sent it and what it does in the loop."""
    if isinstance(msg, HumanMessage):
        return "HUMAN REQUEST"
    if isinstance(msg, AIMessage) and msg.tool_calls:
        return "MODEL DECIDES TO CALL A TOOL"
    if isinstance(msg, ToolMessage):
        return "TOOL RESULT"
    return "FINAL ANSWER"


QUESTIONS = [
    "What documents do I need for a loan?",
    "What is the EMI for 5 lakh at 11% for 36 months?",
]

for question in QUESTIONS:
    print("=" * 60)
    print("Q:", question)
    print("=" * 60)

    result = agent.invoke({"messages": [{"role": "user", "content": question}]})

    for i, msg in enumerate(result["messages"], start=1):
        if isinstance(msg, AIMessage) and msg.tool_calls:
            text = ", ".join(f"{c['name']}({c['args']})" for c in msg.tool_calls)
        else:
            text = msg.content
        print(f"{i}. {label(msg):<29}| {text}")
    print()
