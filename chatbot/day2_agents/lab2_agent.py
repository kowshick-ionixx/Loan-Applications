from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool

load_dotenv()
model = init_chat_model("ollama:qwen3.5:9b", reasoning=False, temperature=0)


@tool
def emi_calculator(
    principal: float, annual_rate_percent: float, tenure_months: int
) -> float:
    """Calculate the monthly EMI of a loan.
    principal is in rupees, annual_rate_percent is like 11 for 11 percent,
    tenure_months is the loan length in months."""
    r = annual_rate_percent / (12 * 100)
    factor = (1 + r) ** tenure_months
    return round(principal * r * factor / (factor - 1), 2)


agent = create_agent(
    model,
    tools=[emi_calculator],
    system_prompt="You are a careful loan assistant. Use tools for every calculation. Never guess numbers.",
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "EMI for 5 lakh at 11% for 3 years?"}]}
)
answer = result["messages"][-1].content
print(answer)

digits = answer.replace(",", "")
assert (
    "16369" in digits or "16370" in digits
), "answer should match Lab 1 (about 16,370)"
print("\nAssert passed: matches Lab 1.")
