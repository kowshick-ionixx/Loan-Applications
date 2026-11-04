"""Day 2: tools against the oracle (seeded test DB), then the agent (llm)."""

import random

import factories
import oracle
import pytest
from loan_agent import get_customer
from support import mentions_amount, rule_keys
from tools import check_eligibility, emi_calculator

ELIGIBILITY_ORDER = ["get_customer", "emi_calculator", "check_eligibility"]


def generated_loan(thresholds, seed: int):
    """A valid (principal, rate, tenure) drawn inside the policy limits."""
    rng = random.Random(seed)
    principal = rng.randrange(
        thresholds["min_amount"], thresholds["high_value_limit"], 10000
    )
    rate = round(rng.uniform(8, 16), 1)
    tenure = rng.randrange(thresholds["min_tenure"], thresholds["max_tenure"] + 1, 12)
    return principal, rate, tenure


def emi_tool(principal, rate, n):
    return emi_calculator.invoke(
        {"principal": principal, "annual_rate_percent": rate, "tenure_months": n}
    )


def lookup(customer_id):
    return get_customer.invoke({"customer_id": str(customer_id)})


def eligibility(record, new_emi):
    return check_eligibility.invoke(
        {
            "age": record["age"],
            "monthly_income": record["monthly_income"],
            "existing_emi": record["existing_emi"],
            "credit_score": record["credit_score"],
            "new_emi": new_emi,
        }
    )


# ---------- unit (seeded, no model) ----------


@pytest.mark.seeded
@pytest.mark.parametrize("seed", range(5))
def test_d2_u1_emi_matches_oracle(thresholds, seed):
    principal, rate, n = generated_loan(thresholds, seed)
    assert abs(emi_tool(principal, rate, n) - oracle.emi(principal, rate, n)) <= 1


@pytest.mark.seeded
def test_d2_u2_negative_tenure_is_a_friendly_message():
    assert emi_tool(500000, 11, -12) == "Tenure must be positive"


@pytest.mark.seeded
def test_d2_u3_get_customer_reads_the_seeded_row(factory):
    seeded = factory.eligible()
    found = lookup(seeded.id)
    assert found["customer_id"] == seeded.id
    assert found["age"] == seeded.age
    assert found["monthly_income"] == seeded.monthly_income
    assert found["credit_score"] == seeded.credit_score
    assert found["existing_emi"] == seeded.existing_emi


@pytest.mark.seeded
@pytest.mark.parametrize("customer_id", ["TEST-DOES-NOT-EXIST", "unknown-number"])
def test_d2_u4_unknown_customer(customer_id):
    if customer_id == "unknown-number":
        customer_id = str(factories.unknown_customer_id())
    result = lookup(customer_id)
    assert isinstance(result, str)
    assert "not found" in result


SCENARIOS = [
    "eligible",
    "low_credit_refer",
    "very_low_credit",
    "underage",
    "overage",
    "low_income",
    "burden_fail",
    "multi_fail",
]


def build(factory, scenario, amount, tenure):
    builder = getattr(factory, scenario)
    if scenario in ("burden_fail", "multi_fail"):
        return builder(amount, tenure)
    return builder()


@pytest.mark.seeded
@pytest.mark.parametrize("scenario", SCENARIOS)
def test_d2_u5_check_eligibility_matches_oracle(factory, thresholds, scenario):
    amount, tenure = thresholds["min_amount"] * 6, 36
    seeded = build(factory, scenario, amount, tenure)
    record = lookup(seeded.id)
    new_emi = emi_tool(amount, thresholds["rate"], tenure)
    result = eligibility(record, new_emi)
    oracle_rules = {**thresholds, "min_credit": thresholds["agent_min_credit"]}
    expected = oracle.eligibility_failures(seeded.record, new_emi, oracle_rules)
    assert rule_keys(result["failed_rules"]) == expected
    assert result["eligible"] is (not expected)


@pytest.mark.seeded
def test_d2_u6_multi_fail_lists_both_failures(factory, thresholds):
    amount, tenure = thresholds["min_amount"] * 6, 36
    seeded = factory.multi_fail(amount, tenure)
    result = eligibility(
        lookup(seeded.id), emi_tool(amount, thresholds["rate"], tenure)
    )
    assert {"credit", "burden"} <= rule_keys(result["failed_rules"])


@pytest.mark.seeded
def test_d2_u7_no_stale_customer_data(factory):
    seeded = factory.eligible()
    assert lookup(seeded.id)["credit_score"] == seeded.credit_score
    factories.set_credit_score(seeded.id, seeded.credit_score - 100)
    assert lookup(seeded.id)["credit_score"] == seeded.credit_score - 100


# ---------- agent (llm) ----------


@pytest.mark.llm
@pytest.mark.seeded
def test_d2_1_emi_question(chat, thresholds):
    principal, rate, n = generated_loan(thresholds, 11)
    answer, tools, _ = chat(f"EMI for {principal} at {rate}% for {n} months?")
    assert tools == ["emi_calculator"]
    assert mentions_amount(answer, oracle.emi(principal, rate, n))


@pytest.mark.llm
@pytest.mark.seeded
def test_d2_2_eligible_customer(chat, factory, thresholds):
    seeded = factory.eligible()
    principal, rate, n = generated_loan(thresholds, 12)
    answer, tools, _ = chat(
        f"Is customer {seeded.id} eligible for {principal} at {rate}% for {n} months?"
    )
    assert tools == ELIGIBILITY_ORDER
    assert "not eligible" not in answer.lower()
    assert "eligible" in answer.lower()


@pytest.mark.llm
@pytest.mark.seeded
def test_d2_3_multi_fail_customer(chat, factory, thresholds):
    amount, rate, n = thresholds["min_amount"] * 6, thresholds["rate"], 36
    seeded = factory.multi_fail(amount, n)
    answer, tools, _ = chat(
        f"Is customer {seeded.id} eligible for {amount} at {rate}% for {n} months?"
    )
    lower = answer.lower()
    assert tools == ELIGIBILITY_ORDER
    assert "not eligible" in lower
    assert "credit score" in lower
    assert "burden" in lower or f"{thresholds['burden_pct']}%" in lower


@pytest.mark.llm
@pytest.mark.seeded
def test_d2_4_unknown_customer(chat):
    unknown = factories.unknown_customer_id()
    answer, tools, _ = chat(f"Is customer {unknown} eligible for a loan?")
    assert "not found" in answer.lower()
    assert str(unknown) in answer
    assert "check_eligibility" not in tools


@pytest.mark.llm
def test_d2_5_off_topic(chat):
    answer, tools, _ = chat("What is the capital of France?")
    assert tools == []
    assert "paris" not in answer.lower()
    assert "loan" in answer.lower()


@pytest.mark.llm
def test_d2_6_missing_details(chat):
    answer, tools, _ = chat("Can I get a loan?")
    lower = answer.lower()
    assert tools == []
    assert "customer id" in lower
    assert "amount" in lower
    assert "tenure" in lower or "months" in lower
