from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.messages import AIMessage, HumanMessage, ToolMessage
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
    r = annual_rate_percent / (12 * 100)  # yearly percent -> monthly decimal
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


def label(msg) -> str:
    """Name each message by who sent it and what it does in the loop."""
    if isinstance(msg, HumanMessage):
        return "HUMAN REQUEST"
    if isinstance(msg, AIMessage) and msg.tool_calls:
        return "MODEL DECIDES TO CALL A TOOL"
    if isinstance(msg, ToolMessage):
        return "TOOL RESULT"
    return "FINAL ANSWER"


labels = []
for i, msg in enumerate(result["messages"], start=1):
    labels.append(label(msg))
    if isinstance(msg, AIMessage) and msg.tool_calls:
        text = ", ".join(f"{c['name']}({c['args']})" for c in msg.tool_calls)
    else:
        text = msg.content
    print(f"{i}. {labels[-1]:<29}| {type(msg).__name__:<12}| {text}")

assert labels == [
    "HUMAN REQUEST",
    "MODEL DECIDES TO CALL A TOOL",
    "TOOL RESULT",
    "FINAL ANSWER",
], f"expected the four steps of the loop, got {labels}"
print("\nAssert passed: human -> tool call -> tool result -> final answer.")
