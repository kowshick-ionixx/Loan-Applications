from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.messages import ToolMessage
from langchain.tools import tool

load_dotenv()
model = init_chat_model("ollama:qwen3.5:9b", reasoning=False, temperature=0)

QUESTION = "EMI for 5 lakh at 11% for -12 months?"
SYSTEM_PROMPT = "You are a careful loan assistant. Use tools for every calculation. Never guess numbers."


def emi(principal: float, annual_rate_percent: float, tenure_months: int) -> float:
    r = annual_rate_percent / (12 * 100)  # yearly percent -> monthly decimal
    factor = (1 + r) ** tenure_months
    return round(principal * r * factor / (factor - 1), 2)


# Version 1: the tool raises an exception on bad input
@tool("emi_calculator")
def raising_emi_calculator(
    principal: float, annual_rate_percent: float, tenure_months: int
) -> float:
    """Calculate the monthly EMI of a loan.
    principal is in rupees, annual_rate_percent is like 11 for 11 percent,
    tenure_months is the loan length in months."""
    if tenure_months <= 0:
        raise ValueError("Tenure must be positive")
    return emi(principal, annual_rate_percent, tenure_months)


# Version 2: the tool returns a plain message the model can read and act on
@tool("emi_calculator")
def friendly_emi_calculator(
    principal: float, annual_rate_percent: float, tenure_months: int
) -> float | str:
    """Calculate the monthly EMI of a loan.
    principal is in rupees, annual_rate_percent is like 11 for 11 percent,
    tenure_months is the loan length in months."""
    if tenure_months <= 0:
        return "Tenure must be positive"
    return emi(principal, annual_rate_percent, tenure_months)


def run(title: str, tool_to_use):
    print(f"\n===== {title} =====")
    agent = create_agent(model, tools=[tool_to_use], system_prompt=SYSTEM_PROMPT)
    try:
        result = agent.invoke({"messages": [{"role": "user", "content": QUESTION}]})
    except Exception as exc:  # noqa: BLE001
        print(f"CRASHED: {type(exc).__name__}: {exc}")
        return None
    for m in result["messages"]:
        if isinstance(m, ToolMessage):
            print("Tool returned:", m.content)
    print("Final answer:", result["messages"][-1].content)
    return result


run("Version 1: tool raises an exception", raising_emi_calculator)
friendly = run("Version 2: tool returns a friendly message", friendly_emi_calculator)

assert friendly is not None, "version 2 should not crash"
answer = friendly["messages"][-1].content.lower()
assert "tenure" in answer, "version 2: the agent should tell the user to fix the tenure"
print("\nAssert passed: version 2 asks the user to fix the input instead of crashing.")
