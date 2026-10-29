import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.messages import AIMessage, HumanMessage, ToolMessage
from langchain.tools import tool
from sqlalchemy import func, select
from tools import check_eligibility, emi_calculator

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
from loan_application.db import MAX_ID, SessionLocal
from loan_application.models import APPROVED, Customer, Loan
from loan_application.services.loan_service import calculate_age


@tool
def get_customer(customer_id: str) -> dict | str:
    """Look up a bank customer in the database by their customer ID, e.g. '161'.
    Returns their name, age, monthly income in rupees, existing monthly EMI
    in rupees and credit score, or a message saying why it can't.

    customer_id: the customer's ID, a number like '161'
    """
    key = customer_id.strip().upper().removeprefix("C")
    if not key.isdigit() or not 0 < int(key) <= MAX_ID:
        return f"Customer {customer_id} not found"
    with SessionLocal() as db:
        customer = db.get(Customer, int(key))
        if customer is None:
            return f"Customer {key} not found"
        if customer.credit_score is None:
            return f"Customer {key} has no credit score on file, so eligibility can't be checked"
        existing_emi = db.execute(
            select(func.coalesce(func.sum(Loan.emi), 0)).where(
                Loan.customer_id == customer.id, Loan.status == APPROVED
            )
        ).scalar_one()
        return {
            "customer_id": customer.id,
            "name": customer.name,
            "age": calculate_age(
                customer.date_of_birth, datetime.now().astimezone().date()
            ),
            "monthly_income": float(customer.monthly_income),
            "existing_emi": float(existing_emi),
            "credit_score": customer.credit_score,
        }


load_dotenv()
model = init_chat_model("ollama:qwen3.5:9b", reasoning=False, temperature=0)

TRACES_FILE = Path(__file__).resolve().parent / "traces.txt"

SYSTEM_PROMPT = (
    "You are a careful loan assistant at an Indian bank. Amounts are in rupees.\n"
    "Rules:\n"
    "- Use tools for every number. NEVER calculate, estimate or guess a number yourself.\n"
    "- To check eligibility, call the tools in this order: get_customer, then "
    "emi_calculator, then check_eligibility with the values the first two returned.\n"
    "- If the customer is not eligible, list every failed rule the tool returned.\n"
    "- If a customer is not found, say so plainly. Never invent customer details.\n"
    "- If information is missing, ask the user for every missing detail in one "
    "message (customer ID, loan amount, interest rate, tenure in months). "
    "Never call a tool with a guessed value.\n"
    "- Only help with loan topics. For anything else, politely decline and do NOT "
    "answer it, not even briefly.\n"
    "- Keep answers short."
)

agent = create_agent(
    model,
    tools=[get_customer, emi_calculator, check_eligibility],
    system_prompt=SYSTEM_PROMPT,
)

QUESTIONS = [
    "EMI for 3,00,000 at 10.5% for 24 months?",
    "Is customer 161 eligible for 5,00,000 at 11% for 36 months?",
    "Is customer 162 eligible for 6,00,000 at 11% for 24 months?",
    "Is customer 999 eligible for a loan?",
    "What is the capital of France?",
    "Can I get a loan?",
]


def ask(question: str) -> list:
    """Run one question through the agent and return every message. One retry, then a fallback."""
    for attempt in (1, 2):
        try:
            result = agent.invoke({"messages": [{"role": "user", "content": question}]})
            return result["messages"]
        except Exception as exc:  # noqa: BLE001
            print(f"  attempt {attempt} failed: {exc}")
    return [
        HumanMessage(question),
        AIMessage("Sorry, I couldn't process that request."),
    ]


def tools_in_order(messages: list) -> list[str]:
    """Every tool the model asked for, in the order it asked."""
    return [
        c["name"] for m in messages if isinstance(m, AIMessage) for c in m.tool_calls
    ]


def format_trace(i: int, messages: list) -> str:
    """One question's full loop, labelled step by step."""
    lines = [f"===== Q{i}: {messages[0].content} ====="]
    for m in messages[1:]:
        if isinstance(m, AIMessage) and m.tool_calls:
            for c in m.tool_calls:
                lines.append(f"  model calls tool : {c['name']}({c['args']})")
        elif isinstance(m, ToolMessage):
            lines.append(f"  tool result      : {m.content}")
        elif isinstance(m, AIMessage):
            lines.append(f"  final answer     : {m.content.strip()}")
    lines.append(f"  tools in order   : {', '.join(tools_in_order(messages)) or '-'}")
    return "\n".join(lines)


def run_tests() -> None:
    """The guide's six questions: print the traces, save traces.txt, check every row."""
    all_messages = []
    for i, q in enumerate(QUESTIONS, start=1):
        print(f"[{i}/{len(QUESTIONS)}] {q}")
        all_messages.append(ask(q))

    traces = "\n\n".join(
        format_trace(i, msgs) for i, msgs in enumerate(all_messages, start=1)
    )
    print("\n" + traces)
    TRACES_FILE.write_text(traces + "\n", encoding="utf-8")
    print(f"\nSaved to {TRACES_FILE.name}")

    tools = [tools_in_order(msgs) for msgs in all_messages]
    answers = [msgs[-1].content for msgs in all_messages]
    lower = [a.lower() for a in answers]
    elig = ["get_customer", "emi_calculator", "check_eligibility"]

    expected = emi_calculator.invoke(
        {"principal": 300000, "annual_rate_percent": 10.5, "tenure_months": 24}
    )
    assert tools[0] == [
        "emi_calculator"
    ], f"Q1 should be one emi_calculator call, got {tools[0]}"
    assert (
        f"{expected:,.2f}" in answers[0] or str(expected) in answers[0]
    ), f"Q1 should state the EMI {expected}"

    assert tools[1] == elig, f"Q2 should call {elig} in order, got {tools[1]}"
    assert "not eligible" not in lower[1], "Q2: customer 161 is eligible"

    assert tools[2] == elig, f"Q3 should call {elig} in order, got {tools[2]}"
    assert "not eligible" in lower[2], "Q3: customer 162 is not eligible"
    assert "credit score" in lower[2], "Q3 should list the credit score failure"
    assert (
        "burden" in lower[2] or "50%" in lower[2]
    ), "Q3 should list the burden failure"

    assert "get_customer" in tools[3], f"Q4 should look the customer up, got {tools[3]}"
    assert (
        "check_eligibility" not in tools[3]
    ), "Q4: no eligibility check for an unknown customer"
    assert (
        "not found" in lower[3]
        or "couldn't find" in lower[3]
        or "could not find" in lower[3]
    ), "Q4 should say the customer was not found"

    assert not tools[4], f"Q5 shouldn't use any tool, got {tools[4]}"
    assert "paris" not in lower[4], "Q5 should decline, not answer the question"

    assert not tools[5], f"Q6 shouldn't call any tool, got {tools[5]}"
    assert (
        "?" in answers[5] or "provide" in lower[5]
    ), "Q6 should ask the user for the missing details"
    assert "customer id" in lower[5], "Q6 should ask for the customer ID"

    print("\nAll asserts passed.")


def chat() -> None:
    """Type your own questions. The agent remembers the conversation until you type exit."""
    print("Loan Helper Agent. Ask any question, or type 'exit' to quit.")
    history = []
    while True:
        try:
            question = input("\nYou   : ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question.lower() in ("exit", "quit"):
            break
        if not question:
            continue

        history.append(HumanMessage(question))
        start = len(history)
        try:
            history = agent.invoke({"messages": history})["messages"]
        except Exception as exc:  # noqa: BLE001
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
    start = datetime.now().astimezone()
    print(f"Start time: {start:%Y-%m-%d %H:%M:%S}\n")
    try:
        if "--chat" in sys.argv:
            chat()
        else:
            run_tests()
    finally:
        end = datetime.now().astimezone()
        print(f"\nEnd time  : {end:%Y-%m-%d %H:%M:%S}")
        print(f"Time taken: {(end - start).total_seconds():.1f} seconds")
