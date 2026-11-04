"""Day 4: the pre-screening graph against the oracle (seeded test DB)."""

import factories
import oracle
import pytest
from support import rule_keys

pytestmark = pytest.mark.seeded


def run_scenario(graph, thread_id, run_case, fake_reader, customer_id, amount, tenure):
    fake_reader(amount, tenure)
    events, snapshot = run_case(graph, thread_id, customer_id)
    if snapshot.interrupts:
        return "refer", events, snapshot
    return snapshot.values["decision"], events, snapshot


def expected(seeded, amount, tenure, t):
    record = seeded.record if seeded else None
    decision = oracle.expected_route(record, amount, tenure, t)
    failures = (
        oracle.graph_failures(record, amount, tenure, t)
        if decision == "reject"
        else set()
    )
    return decision, failures


def assert_matches_oracle(
    graph, thread_id, run_case, fake_reader, t, seeded, amount, tenure
):
    customer_id = seeded.id if seeded else factories.unknown_customer_id()
    decision, events, snapshot = run_scenario(
        graph, thread_id, run_case, fake_reader, customer_id, amount, tenure
    )
    want, want_failures = expected(seeded, amount, tenure, t)
    assert decision == want
    if want == "reject":
        assert rule_keys(snapshot.values["failed_rules"]) == want_failures
    return decision, events, snapshot


def normal_loan(t):
    return t["min_amount"] * 6, 36


def test_d4_u1_eligible_is_approved(
    graph, thread_id, run_case, fake_reader, thresholds, factory
):
    amount, tenure = normal_loan(thresholds)
    decision, *_ = assert_matches_oracle(
        graph,
        thread_id,
        run_case,
        fake_reader,
        thresholds,
        factory.eligible(),
        amount,
        tenure,
    )
    assert decision == "approve"


def test_d4_u2_high_value_is_referred(
    graph, thread_id, run_case, fake_reader, thresholds, factory
):
    amount = thresholds["high_value_limit"] + thresholds["min_amount"]
    decision, *_ = assert_matches_oracle(
        graph,
        thread_id,
        run_case,
        fake_reader,
        thresholds,
        factory.eligible(),
        amount,
        60,
    )
    assert decision == "refer"


def test_d4_u3_reject_beats_refer(
    graph, thread_id, run_case, fake_reader, thresholds, factory
):
    amount, tenure = normal_loan(thresholds)
    refer_band = (thresholds["refer_from"] + thresholds["min_credit"]) // 2
    seeded = factory.burden_fail(amount, tenure, credit_score=refer_band)
    decision, _, snapshot = assert_matches_oracle(
        graph, thread_id, run_case, fake_reader, thresholds, seeded, amount, tenure
    )
    assert decision == "reject"
    assert "burden" in rule_keys(snapshot.values["failed_rules"])


def test_d4_u4_low_credit_is_referred(
    graph, thread_id, run_case, fake_reader, thresholds, factory
):
    amount, tenure = normal_loan(thresholds)
    decision, *_ = assert_matches_oracle(
        graph,
        thread_id,
        run_case,
        fake_reader,
        thresholds,
        factory.low_credit_refer(),
        amount,
        tenure,
    )
    assert decision == "refer"


def test_d4_u5_missing_amount_and_tenure(
    graph, thread_id, run_case, fake_reader, thresholds, factory
):
    decision, *_ = assert_matches_oracle(
        graph,
        thread_id,
        run_case,
        fake_reader,
        thresholds,
        factory.eligible(),
        None,
        None,
    )
    assert decision == "need_info"


def test_d4_u6_unknown_customer(graph, thread_id, run_case, fake_reader, thresholds):
    amount, tenure = normal_loan(thresholds)
    decision, *_ = assert_matches_oracle(
        graph, thread_id, run_case, fake_reader, thresholds, None, amount, tenure
    )
    assert decision == "need_info"


def test_d4_u7_very_low_credit_is_rejected(
    graph, thread_id, run_case, fake_reader, thresholds, factory
):
    amount, tenure = normal_loan(thresholds)
    decision, _, snapshot = assert_matches_oracle(
        graph,
        thread_id,
        run_case,
        fake_reader,
        thresholds,
        factory.very_low_credit(),
        amount,
        tenure,
    )
    assert decision == "reject"
    assert "credit" in rule_keys(snapshot.values["failed_rules"])


@pytest.mark.parametrize(
    ("scenario", "rule"),
    [("underage", "age"), ("overage", "age"), ("low_income", "income")],
)
def test_d4_u8_age_and_income_rejects(
    graph, thread_id, run_case, fake_reader, thresholds, factory, scenario, rule
):
    amount, tenure = thresholds["min_amount"], 12
    seeded = getattr(factory, scenario)()
    decision, _, snapshot = assert_matches_oracle(
        graph, thread_id, run_case, fake_reader, thresholds, seeded, amount, tenure
    )
    assert decision == "reject"
    assert rule in rule_keys(snapshot.values["failed_rules"])


BOUNDARIES = [
    "credit_at_refer_from",
    "credit_at_min_credit",
    "amount_at_limit",
    "burden_at_limit",
]


@pytest.mark.parametrize("boundary", BOUNDARIES)
def test_d4_u9_boundaries(
    graph, thread_id, run_case, fake_reader, thresholds, factory, boundary
):
    t = thresholds
    amount, tenure = normal_loan(t)
    if boundary == "credit_at_refer_from":
        seeded = factory.make_customer(credit_score=t["refer_from"])
    elif boundary == "credit_at_min_credit":
        seeded = factory.make_customer(credit_score=t["min_credit"])
    elif boundary == "amount_at_limit":
        amount, tenure = t["high_value_limit"], 60
        seeded = factory.make_customer(monthly_income=t["min_income"] * 8)
    else:
        seeded = factory.burden_at_limit(amount, tenure)
    decision, *_ = assert_matches_oracle(
        graph, thread_id, run_case, fake_reader, t, seeded, amount, tenure
    )
    print(f"{boundary}: oracle and graph both say {decision}")


def test_d4_u10_log_appends_in_node_order(
    graph, thread_id, run_case, fake_reader, thresholds, factory
):
    amount, tenure = normal_loan(thresholds)
    _, events, snapshot = run_scenario(
        graph, thread_id, run_case, fake_reader, factory.eligible().id, amount, tenure
    )
    nodes_run = [node for node, _ in events]
    log = snapshot.values["log"]
    assert nodes_run == ["intake", "validate", "score", "approve"]
    assert [line.split(":")[0] for line in log] == nodes_run
    for (node, update), line in zip(events, log, strict=True):
        assert update["log"] == [line], f"{node} must append exactly its own line"


def test_d4_u11_diagram_has_every_node_and_route(graph):
    mermaid = graph.get_graph().draw_mermaid()
    for node in [
        "intake",
        "validate",
        "score",
        "approve",
        "refer",
        "reject",
        "need_info",
    ]:
        assert node in mermaid
    assert "validate -.-> need_info" in mermaid
    assert "score -.-> refer" in mermaid


# ---------- the same scenarios from natural-language emails (llm) ----------

EMAIL_SCENARIOS = [
    "eligible",
    "high_value",
    "burden",
    "low_credit",
    "missing",
    "unknown",
]


@pytest.mark.llm
@pytest.mark.parametrize("scenario", EMAIL_SCENARIOS)
def test_d4_l_decisions_from_emails(
    graph, thread_id, run_case, thresholds, factory, scenario
):
    t = thresholds
    amount, tenure = normal_loan(t)
    seeded = None
    if scenario == "eligible":
        seeded = factory.eligible()
    elif scenario == "high_value":
        amount, tenure, seeded = (
            t["high_value_limit"] + t["min_amount"],
            60,
            factory.eligible(),
        )
    elif scenario == "burden":
        seeded = factory.burden_fail(amount, tenure)
    elif scenario == "low_credit":
        seeded = factory.low_credit_refer()
    elif scenario == "missing":
        seeded = factory.eligible()
    email = (
        "Hi, I would like a loan for a new car."
        if scenario == "missing"
        else f"Hello, I need a loan of Rs {amount:,} for {tenure} months for home repairs."
    )
    customer_id = seeded.id if seeded else factories.unknown_customer_id()
    _, snapshot = run_case(graph, thread_id, customer_id, email)
    decision = "refer" if snapshot.interrupts else snapshot.values["decision"]
    want_amount = None if scenario == "missing" else amount
    want_tenure = None if scenario == "missing" else tenure
    want, _ = expected(seeded, want_amount, want_tenure, t)
    enquiry = snapshot.values["enquiry"]
    assert (enquiry.amount, enquiry.tenure_months) == (want_amount, want_tenure)
    assert decision == want
