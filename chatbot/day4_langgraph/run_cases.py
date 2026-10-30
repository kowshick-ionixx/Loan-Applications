from pathlib import Path

from prescreen_graph import after_validate, graph, route
from nodes import approve, need_info, refer, reject, score, validate
from enquiry_reader import LoanEnquiry

OUTPUT_FILE = Path(__file__).resolve().parent / "test_output.txt"

CASES = [
    ("161", "Hi, I need a loan of 5 lakh rupees for 3 years to renovate my house.", "approve"),
    ("161", "Looking for Rs 12,00,000 personal loan, repayment over 60 months.", "refer"),
    ("162", "I need 10 lakh for 36 months for my business.", "reject"),
    ("162", "Need 2 lakh, can repay in 24 months.", "refer"),
    ("161", "I want a loan for a car", "need_info"),
    ("999", "I need 3 lakh for 2 years.", "need_info"),
]

# Rules no database customer reaches, checked without the model. The first row is
# the guide's case 4 customer (C105, credit score 670), used only as test input.
GUIDE_C105 = {"name": "Meera Iyer", "age": 33, "monthly_income": 70000, "existing_emi": 8000, "credit_score": 670}
RULE_CHECKS = [
    ("credit score 670 (policy 1.3)", GUIDE_C105, 300000, 36, "refer"),
    ("credit score 719 (policy 1.3)", {**GUIDE_C105, "credit_score": 719}, 300000, 36, "refer"),
    ("credit score 720 (eligible)", {**GUIDE_C105, "credit_score": 720}, 300000, 36, "approve"),
    ("credit score 640", {**GUIDE_C105, "credit_score": 640}, 300000, 36, "reject"),
    ("amount 20,00,000 (policy 2.1)", GUIDE_C105, 2000000, 60, "reject"),
    ("tenure 72 months (policy 2.2)", GUIDE_C105, 300000, 72, "reject"),
]
OUTCOMES = {"approve": approve, "refer": refer, "reject": reject}


def check_rule(customer: dict, amount: float, tenure: int) -> dict:
    """Run score and route on a hand-made customer, with no model and no database."""
    state = {
        "enquiry": LoanEnquiry(amount=amount, tenure_months=tenure, confidence="high"),
        "customer": customer,
        "log": [],
    }
    state |= score(state)
    return state | OUTCOMES[route(state)](state)


def check_bad_input(customer_id: str, amount: float, tenure: int) -> dict:
    """Run validate on a live customer with an amount or tenure that is not above 0."""
    state = {
        "customer_id": customer_id,
        "enquiry": LoanEnquiry(amount=amount, tenure_months=tenure, confidence="high"),
        "log": [],
    }
    state |= validate(state)
    assert after_validate(state) == "need_info"
    return state | need_info(state)


def format_case(i: int, customer_id: str, email: str, expected: str, result: dict) -> str:
    mark = "OK" if result["decision"] == expected else "MISMATCH"
    lines = [
        f"===== Case {i}: customer {customer_id}, expected {expected} =====",
        f"Email    : {email}",
        f"Decision : {result['decision']}  [{mark}]",
        f"Reason   : {result['reason']}",
        "Log:",
    ]
    lines += [f"  {entry}" for entry in result["log"]]
    return "\n".join(lines)


if __name__ == "__main__":
    blocks = []
    results = []
    for i, (customer_id, email, expected) in enumerate(CASES, start=1):
        print(f"[{i}/{len(CASES)}] customer {customer_id}: {email}")
        result = graph.invoke({"customer_id": customer_id, "email": email, "log": []})
        results.append(result)
        blocks.append(format_case(i, customer_id, email, expected, result))

    matched = sum(r["decision"] == c[2] for r, c in zip(results, CASES))
    report = "\n\n".join(blocks) + f"\n\n{matched}/{len(CASES)} decisions match.\n"

    rule_lines = ["", "===== Rule checks (no model) ====="]
    rule_results = []
    for label, customer, amount, tenure, expected in RULE_CHECKS:
        result = check_rule(customer, amount, tenure)
        rule_results.append((label, result["decision"], expected))
        mark = "OK" if result["decision"] == expected else "MISMATCH"
        rule_lines.append(f"{label:<32} -> {result['decision']:<9} [{mark}]  {result['reason']}")
    for label, amount, tenure in [("amount 0", 0, 36), ("tenure -12", 500000, -12)]:
        result = check_bad_input("161", amount, tenure)
        rule_results.append((label, result["decision"], "need_info"))
        mark = "OK" if result["decision"] == "need_info" else "MISMATCH"
        rule_lines.append(f"{label:<32} -> {result['decision']:<9} [{mark}]  {result['reason']}")
    report += "\n".join(rule_lines) + "\n"
    print("\n" + report)
    OUTPUT_FILE.write_text(report, encoding="utf-8")
    print(f"Saved to {OUTPUT_FILE.name}")

    for i, (result, (_, _, expected)) in enumerate(zip(results, CASES), start=1):
        assert result["decision"] == expected, (
            f"case {i}: expected {expected}, got {result['decision']}"
        )
    for i in (5, 6):
        assert not any(e.startswith("score") for e in results[i - 1]["log"]), (
            f"case {i} should skip score"
        )
    for label, got, expected in rule_results:
        assert got == expected, f"{label}: expected {expected}, got {got}"
    print("\nAll asserts passed.")
