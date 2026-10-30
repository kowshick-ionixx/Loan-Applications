import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "day2_agents"))

from state import LoanState
from enquiry_reader import read_enquiry
from loan_agent import get_customer
from tools import MAX_AGE, MAX_BURDEN_PERCENT, MIN_AGE, MIN_INCOME, emi_calculator

RATE_PERCENT = 11
MIN_CREDIT_SCORE = 650
ELIGIBLE_SCORE = 720
REFER_SCORE_MAX = ELIGIBLE_SCORE - 1
REFER_AMOUNT = 1_000_000
MIN_AMOUNT = 50_000
MAX_AMOUNT = 1_500_000
MIN_TENURE = 12
MAX_TENURE = 60


def refer_reasons(state: LoanState) -> list[str]:
    """Why a case needs a human to decide. Empty means no referral needed."""
    reasons = []
    credit = state["customer"]["credit_score"]
    if MIN_CREDIT_SCORE <= credit <= REFER_SCORE_MAX:
        reasons.append(
            f"credit score {credit} is between {MIN_CREDIT_SCORE} and {REFER_SCORE_MAX} (policy 1.3)"
        )
    amount = state["enquiry"].amount
    if amount > REFER_AMOUNT:
        reasons.append(f"amount {amount:,.0f} is above {REFER_AMOUNT:,} (policy 2.3)")
    return reasons


def intake(state: LoanState):
    enquiry = read_enquiry(state["email"])
    return {
        "enquiry": enquiry,
        "log": [
            f"intake: amount={enquiry.amount}, tenure={enquiry.tenure_months}, "
            f"missing={enquiry.missing_fields}"
        ],
    }


def validate(state: LoanState):
    enquiry = state["enquiry"]
    problems = []
    if enquiry.amount is None:
        problems.append("missing loan amount")
    elif enquiry.amount <= 0:
        problems.append("loan amount must be above 0")
    if enquiry.tenure_months is None:
        problems.append("missing tenure")
    elif enquiry.tenure_months <= 0:
        problems.append("tenure must be above 0")

    found = get_customer.invoke({"customer_id": state["customer_id"]})
    if isinstance(found, dict):
        customer = found
    else:
        customer = None
        problems.append(found)

    if problems:
        line = "validate: " + "; ".join(problems)
    else:
        line = f"validate: ok, customer {customer['name']}"
    return {"customer": customer, "problems": problems, "log": [line]}


def score(state: LoanState):
    enquiry = state["enquiry"]
    customer = state["customer"]
    emi = emi_calculator.invoke(
        {
            "principal": enquiry.amount,
            "annual_rate_percent": RATE_PERCENT,
            "tenure_months": enquiry.tenure_months,
        }
    )
    if isinstance(emi, str):
        return {"emi": 0.0, "failed_rules": [emi], "log": [f"score: {emi}"]}

    age = customer["age"]
    income = customer["monthly_income"]
    credit = customer["credit_score"]
    failed_rules = []
    if not MIN_AMOUNT <= enquiry.amount <= MAX_AMOUNT:
        failed_rules.append(
            f"Amount {enquiry.amount:,.0f} is outside {MIN_AMOUNT:,} to {MAX_AMOUNT:,} (policy 2.1)"
        )
    if not MIN_TENURE <= enquiry.tenure_months <= MAX_TENURE:
        failed_rules.append(
            f"Tenure {enquiry.tenure_months} months is outside {MIN_TENURE} to {MAX_TENURE} (policy 2.2)"
        )
    if not MIN_AGE <= age <= MAX_AGE:
        failed_rules.append(f"Age {age} is outside {MIN_AGE} to {MAX_AGE}")
    if income < MIN_INCOME:
        failed_rules.append(f"Monthly income {income:,.0f} is below {MIN_INCOME:,}")
    if credit < MIN_CREDIT_SCORE:
        failed_rules.append(f"Credit score {credit} is below {MIN_CREDIT_SCORE}")
    burden = (customer["existing_emi"] + emi) / income * 100 if income > 0 else 100.0
    if burden > MAX_BURDEN_PERCENT:
        failed_rules.append(
            f"EMI burden {burden:.1f}% is above {MAX_BURDEN_PERCENT}% of income"
        )

    line = f"score: EMI {emi:,.2f}, burden {burden:.1f}%, failed={failed_rules}"
    return {"emi": emi, "failed_rules": failed_rules, "log": [line]}


def approve(state: LoanState):
    reason = (
        f"All eligibility rules passed. Monthly EMI {state['emi']:,.2f} at {RATE_PERCENT}%."
    )
    return {"decision": "approve", "reason": reason, "log": ["approve"]}


def refer(state: LoanState):
    reason = "Referred for review: " + "; ".join(refer_reasons(state)) + "."
    return {"decision": "refer", "reason": reason, "log": ["refer"]}


def reject(state: LoanState):
    reason = "Not eligible: " + "; ".join(state["failed_rules"]) + "."
    return {"decision": "reject", "reason": reason, "log": ["reject"]}


def need_info(state: LoanState):
    reason = "More information needed: " + "; ".join(state["problems"]) + "."
    return {"decision": "need_info", "reason": reason, "log": ["need_info"]}

