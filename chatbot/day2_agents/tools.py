from langchain.tools import tool

MIN_AGE = 21
MAX_AGE = 60
MIN_INCOME = 25000
MIN_CREDIT_SCORE = 715
MAX_BURDEN_PERCENT = 50


@tool
def emi_calculator(
    principal: float, annual_rate_percent: float, tenure_months: int
) -> float | str:
    """Calculate the monthly EMI of a loan.
    principal is in rupees, annual_rate_percent is like 11 for 11 percent,
    tenure_months is the loan length in months."""
    if principal <= 0:
        return "Principal must be positive"
    if tenure_months <= 0:
        return "Tenure must be positive"
    if annual_rate_percent < 0:
        return "Interest rate cannot be negative"
    if annual_rate_percent == 0:
        return round(principal / tenure_months, 2)
    r = annual_rate_percent / (12 * 100)
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

    def emi(principal, rate, months):
        return emi_calculator.invoke(
            {
                "principal": principal,
                "annual_rate_percent": rate,
                "tenure_months": months,
            }
        )

    emi_5l = emi(500000, 11, 36)
    emi_6l = emi(600000, 11, 24)
    print("EMI 5L, 11%, 36m:", emi_5l)
    print("EMI 6L, 11%, 24m:", emi_6l)
    print("EMI tenure -12:  ", emi(500000, 11, -12))
    assert abs(emi_5l - 16370) < 5, f"guide says about 16,370, got {emi_5l}"
    assert emi(500000, 11, -12) == "Tenure must be positive"

    def eligibility(age, monthly_income, existing_emi, credit_score, new_emi):
        return check_eligibility.invoke(
            {
                "age": age,
                "monthly_income": monthly_income,
                "existing_emi": existing_emi,
                "credit_score": credit_score,
                "new_emi": new_emi,
            }
        )

    good = eligibility(24, 100000, 4660.78, 725, emi_5l)
    bad = eligibility(24, 45000, 0, 701, emi_6l)
    print("\nScore 725, income 1L, 5L 36m:", good)
    print("Score 701, income 45k, 6L 24m:", bad)
    assert good["eligible"], "should be eligible"
    assert not bad["eligible"], "should not be eligible"
    assert len(bad["failed_rules"]) == 2, "should fail both credit score and burden"
    assert any("Credit score" in r for r in bad["failed_rules"])
    assert any("burden" in r for r in bad["failed_rules"])

    print("\nAll asserts passed.")
