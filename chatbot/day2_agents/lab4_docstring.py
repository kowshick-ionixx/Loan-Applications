from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.messages import AIMessage
from langchain.tools import tool

load_dotenv()
model = init_chat_model("ollama:qwen3.5:9b", reasoning=False, temperature=0)

QUESTION = "EMI for 5 lakh at 11% for 3 years?"
SYSTEM_PROMPT = "You are a careful loan assistant. Use tools for every calculation. Never guess numbers."


def emi(principal: float, annual_rate_percent: float, tenure_months: int) -> float:
    r = annual_rate_percent / (12 * 100)  # yearly percent -> monthly decimal
    factor = (1 + r) ** tenure_months
    return round(principal * r * factor / (factor - 1), 2)


@tool
def emi_calculator(
    principal: float, annual_rate_percent: float, tenure_months: int
) -> float:
    """Calculate the monthly EMI of a loan.
    principal is in rupees, annual_rate_percent is like 11 for 11 percent,
    tenure_months is the loan length in months."""
    return emi(principal, annual_rate_percent, tenure_months)


# Same name, same code, same args: only the docstring is different
@tool("emi_calculator")
def vague_emi_calculator(
    principal: float, annual_rate_percent: float, tenure_months: int
) -> float:
    """does maths"""
    return emi(principal, annual_rate_percent, tenure_months)


def run(tool_to_use) -> None:
    print(f"\n===== Docstring: {tool_to_use.description.splitlines()[0]!r} =====")
    agent = create_agent(model, tools=[tool_to_use], system_prompt=SYSTEM_PROMPT)
    result = agent.invoke({"messages": [{"role": "user", "content": QUESTION}]})
    calls = [
        c for m in result["messages"] if isinstance(m, AIMessage) for c in m.tool_calls
    ]
    print("Tool calls the model asked for:")
    for c in calls:
        print("  ", c["name"], c["args"])
    if not calls:
        print("   (none: the model answered without the tool)")
    answer = result["messages"][-1].content
    correct = "16369" in answer.replace(",", "") or "16370" in answer.replace(",", "")
    print("Final answer:", answer)
    print("Matches 16,369.36?", "yes" if correct else "NO")


run(emi_calculator)
run(vague_emi_calculator)
print(
    "\nCompare the two runs: did the model still call the tool, send 11 (not 0.11) "
    "and 36 (not 3), and get the right EMI?"
)
