import operator
import sys
from pathlib import Path
from typing import Annotated, TypedDict

sys.path.append(str(Path(__file__).resolve().parent.parent / "day1_langchain"))

from enquiry_reader import LoanEnquiry, read_enquiry
from langgraph.graph import StateGraph, START, END


class State(TypedDict):
    email: str
    enquiry: LoanEnquiry
    log: Annotated[list[str], operator.add]


def read_email(state: State):
    enquiry = read_enquiry(state["email"])
    return {"enquiry": enquiry, "log": ["read_email: model read the email"]}


builder = StateGraph(State)
builder.add_node("read_email", read_email)
builder.add_edge(START, "read_email")
builder.add_edge("read_email", END)
graph = builder.compile()

email = "Hi, I'm Ramesh Kumar. I need a loan of 5 lakh rupees for 3 years to renovate my house."
result = graph.invoke({"email": email, "log": []})

print("Enquiry:", result["enquiry"])
print("Amount:", result["enquiry"].amount)
print("Tenure:", result["enquiry"].tenure_months)
print("Log:", result["log"])
