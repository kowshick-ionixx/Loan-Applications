import sys
from pathlib import Path

from langchain.tools import tool

# Let this file import `data` from the chatbot/ folder, however it is run
sys.path.append(str(Path(__file__).resolve().parent.parent))
from data.customers import CUSTOMERS

# Eligibility rules from the guide
MIN_AGE = 21
MAX_AGE = 60
MIN_INCOME = 25000
MIN_CREDIT_SCORE = 700
MAX_BURDEN_PERCENT = 50


@tool
def get_customer(customer_id: str) -> dict | str:
    """Look up a bank customer by their customer ID, e.g. 'C101'.
    Returns their name, age, monthly income in rupees, existing monthly EMI
    in rupees and credit score, or a 'not found' message.

    customer_id: the customer's ID, like 'C101'
    """
    key = customer_id.strip().upper()
    if key not in CUSTOMERS:
        return f"Customer {key} not found"
    return {"customer_id": key, **CUSTOMERS[key]}


@tool
def emi_calculator(
    principal: float, annual_rate_percent: float, tenure_months: int
) -> float | str:
    """Calculate the monthly EMI of a loan.
    principal is in rupees, annual_rate_percent is like 11 for 11 percent,
    tenure_months is the loan length in months."""
    # Clear messages instead of crashing, so the agent can ask the user to fix the input
    if principal <= 0:
        return "Principal must be positive"
    if tenure_months <= 0:
        return "Tenure must be positive"
    if annual_rate_percent < 0:
        return "Interest rate cannot be negative"
    if annual_rate_percent == 0:
        return round(principal / tenure_months, 2)
    r = annual_rate_percent / (12 * 100)  # yearly percent -> monthly decimal
    factor = (1 + r) ** tenure_months
    return round(principal * r * factor / (factor - 1), 2)


@tool
def check_eligibility(
    age: int,
    monthly_income: float,
    existing_emi: float,
    credit_score: int,
    new_emi: float,
) -> dict:
    """Check a customer against every loan eligibility rule.
    Returns eligible true/false and the list of every rule that failed.

    age: customer's age in years
    monthly_income: monthly income in rupees
    existing_emi: EMI the customer already pays each month, in rupees
    credit_score: credit score, e.g. 745
    new_emi: monthly EMI of the new loan in rupees, from emi_calculator
    """
    failed_rules = []
    if not MIN_AGE <= age <= MAX_AGE:
        failed_rules.append(f"Age {age} is outside {MIN_AGE} to {MAX_AGE}")
    if monthly_income < MIN_INCOME:
        failed_rules.append(
            f"Monthly income {monthly_income:,.0f} is below {MIN_INCOME:,}"
        )
    if credit_score < MIN_CREDIT_SCORE:
        failed_rules.append(f"Credit score {credit_score} is below {MIN_CREDIT_SCORE}")

    burden = (
        (existing_emi + new_emi) / monthly_income * 100 if monthly_income > 0 else 100.0
    )
    if burden > MAX_BURDEN_PERCENT:
        failed_rules.append(
            f"EMI burden {burden:.1f}% is above {MAX_BURDEN_PERCENT}% of income"
        )

    return {
        "eligible": not failed_rules,
        "failed_rules": failed_rules,
        "burden_percent": round(burden, 1),
    }


if __name__ == "__main__":
    # Test the tools by themselves, no AI. Doesn't run when loan_agent.py imports this file.
    print("get_customer C101:", get_customer.invoke({"customer_id": "C101"}))
    print("get_customer c999:", get_customer.invoke({"customer_id": "c999"}))
    assert get_customer.invoke({"customer_id": " c101 "})["name"] == "Ramesh Kumar"
    assert get_customer.invoke({"customer_id": "C999"}) == "Customer C999 not found"

    def emi(principal, rate, months):
        return emi_calculator.invoke(
            {
                "principal": principal,
                "annual_rate_percent": rate,
                "tenure_months": months,
            }
        )

    emi_c101 = emi(500000, 11, 36)
    emi_c103 = emi(400000, 11, 24)
    print("\nEMI 5L, 11%, 36m:", emi_c101)
    print("EMI 4L, 11%, 24m:", emi_c103)
    print("EMI tenure -12:  ", emi(500000, 11, -12))
    assert abs(emi_c101 - 16370) < 5, f"guide says about 16,370, got {emi_c101}"
    assert emi(500000, 11, -12) == "Tenure must be positive"

    def eligibility(customer_id, new_emi):
        c = CUSTOMERS[customer_id]
        return check_eligibility.invoke(
            {
                "age": c["age"],
                "monthly_income": c["monthly_income"],
                "existing_emi": c["existing_emi"],
                "credit_score": c["credit_score"],
                "new_emi": new_emi,
            }
        )

    c101 = eligibility("C101", emi_c101)
    c103 = eligibility("C103", emi_c103)
    print("\nC101, 5L 36m:", c101)
    print("C103, 4L 24m:", c103)
    assert c101["eligible"], "C101 should be eligible"
    assert not c103["eligible"], "C103 should not be eligible"
    assert (
        len(c103["failed_rules"]) == 2
    ), "C103 should fail both credit score and burden"
    assert any("Credit score" in r for r in c103["failed_rules"])
    assert any("burden" in r for r in c103["failed_rules"])

    print("\nAll asserts passed.")
