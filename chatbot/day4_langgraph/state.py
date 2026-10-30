import operator
import sys
from pathlib import Path
from typing import Annotated, TypedDict

sys.path.append(str(Path(__file__).resolve().parent.parent / "day1_langchain"))

from enquiry_reader import LoanEnquiry


class LoanState(TypedDict):
    email: str
    customer_id: str
    enquiry: LoanEnquiry
    customer: dict | None
    problems: list[str]
    emi: float
    failed_rules: list[str]
    decision: str
    reason: str
    log: Annotated[list[str], operator.add]
