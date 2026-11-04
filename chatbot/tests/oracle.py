"""Independent expected results. Plain Python: nothing here imports app code.

Thresholds are passed in (loaded at test time from the app's own constants),
so the oracle never hard-codes a rule value.
"""


def emi(principal: float, annual_rate_percent: float, n: int) -> float:
    """EMI = P*r*(1+r)^n / ((1+r)^n - 1), r = rate / (12*100)."""
    if annual_rate_percent == 0:
        return principal / n
    r = annual_rate_percent / (12 * 100)
    factor = (1 + r) ** n
    return principal * r * factor / (factor - 1)


def emi_paise(principal: float, annual_rate_percent: float, n: int) -> float:
    """The EMI as charged: rounded to paise."""
    return round(emi(principal, annual_rate_percent, n), 2)


def burden_fails(customer: dict, new_emi: float, t: dict) -> bool:
    income = customer["monthly_income"]
    if income <= 0:
        return True
    return (customer["existing_emi"] + new_emi) > t["burden_pct"] / 100 * income


def eligibility_failures(customer: dict, new_emi: float, t: dict) -> set[str]:
    """Day 2 check_eligibility rules: age, income, credit (below min_credit), burden."""
    failed = set()
    if not t["min_age"] <= customer["age"] <= t["max_age"]:
        failed.add("age")
    if customer["monthly_income"] < t["min_income"]:
        failed.add("income")
    if customer["credit_score"] < t["min_credit"]:
        failed.add("credit")
    if burden_fails(customer, new_emi, t):
        failed.add("burden")
    return failed


def graph_failures(customer: dict, amount: float, tenure: int, t: dict) -> set[str]:
    """Day 4 reject rules: the policy's amount and tenure limits (2.1, 2.2),
    age, income, burden, and a credit score below reject_below."""
    failed = set()
    if not t["min_amount"] <= amount <= t["max_amount"]:
        failed.add("amount")
    if not t["min_tenure"] <= tenure <= t["max_tenure"]:
        failed.add("tenure")
    if not t["min_age"] <= customer["age"] <= t["max_age"]:
        failed.add("age")
    if customer["monthly_income"] < t["min_income"]:
        failed.add("income")
    if customer["credit_score"] < t["reject_below"]:
        failed.add("credit")
    if burden_fails(customer, emi_paise(amount, t["rate"], tenure), t):
        failed.add("burden")
    return failed


def expected_route(customer: dict | None, amount, tenure, t: dict) -> str:
    """Priority: need_info, reject, refer, approve."""
    if customer is None or amount is None or tenure is None:
        return "need_info"
    if amount <= 0 or tenure <= 0:
        return "need_info"
    if graph_failures(customer, amount, tenure, t):
        return "reject"
    if t["refer_from"] <= customer["credit_score"] < t["min_credit"]:
        return "refer"
    if amount > t["high_value_limit"]:
        return "refer"
    return "approve"
