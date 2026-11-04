from types import SimpleNamespace

import cases
import pytest
from accounts import BAD_LOGIN, CUSTOMER, MANAGER, UserContext, can_see_customer, login
from approval_graph import DB_PATH, sqlite_graph
from conftest import MANAGER_USER
from enquiry_reader import LoanEnquiry
from nodes import score
from prescreen_graph import route
from ui_helpers import decision_card, rupee

# ---------- D4: rupee formatter ----------


@pytest.mark.parametrize(
    ("amount", "decimals", "expected"),
    [
        (500000, 0, "₹5,00,000"),
        (2500000, 0, "₹25,00,000"),
        (1200000, 0, "₹12,00,000"),
        (16369.357, 2, "₹16,369.36"),
        (999, 0, "₹999"),
        (None, 0, "-"),
    ],
)
def test_rupee_indian_format(amount, decimals, expected):
    assert rupee(amount, decimals) == expected


# ---------- B: routing with a pre-filled enquiry (no model call) ----------


def test_b1_approve_path(graph, prefilled):
    state = prefilled(graph, "b1", "161", 500000, 36)
    assert state.values["decision"] == "approve"
    assert state.next == ()
    steps = [line.split(":")[0] for line in state.values["log"]]
    assert steps == ["intake", "validate", "score", "approve"]


def test_b2_amount_above_ten_lakh_pauses_at_refer(graph, prefilled):
    state = prefilled(graph, "b2", "161", 1200000, 60)
    assert state.next == ("refer",)
    assert "policy 2.3" in state.interrupts[0].value["reason"]
    assert "b2" in cases.waiting_cases(graph)


def test_b3_burden_rule_rejects(graph, prefilled):
    state = prefilled(graph, "b3", "162", 1000000, 36)
    assert state.values["decision"] == "reject"
    assert any("burden" in rule for rule in state.values["failed_rules"])


def test_b4_borderline_credit_score_pauses_at_refer(graph, prefilled):
    state = prefilled(graph, "b4", "162", 200000, 24)
    assert state.next == ("refer",)
    assert "credit score 701" in state.interrupts[0].value["reason"]


@pytest.mark.parametrize(
    ("credit_score", "expected"),
    [(670, "refer"), (719, "refer"), (720, "approve"), (640, "reject")],
)
def test_b4_credit_score_bands_with_hand_made_customer(credit_score, expected):
    """The guide's C105 (credit score 670) is not in the database, so score and
    route get a hand-made customer: credit 650 to 719 refer, 720+ approve."""
    state = {
        "enquiry": LoanEnquiry(amount=300000, tenure_months=36, confidence="high"),
        "customer": {
            "age": 33,
            "monthly_income": 70000,
            "existing_emi": 8000,
            "credit_score": credit_score,
        },
    }
    state |= score(state)
    assert route(state) == expected


def test_b5_missing_amount_and_tenure_needs_info(graph, prefilled):
    state = prefilled(graph, "b5", "161", None, None)
    assert state.values["decision"] == "need_info"
    assert "missing loan amount" in state.values["problems"]
    assert "missing tenure" in state.values["problems"]


def test_b6_unknown_customer_needs_info(graph, prefilled):
    state = prefilled(graph, "b6", "999", 300000, 24)
    assert state.values["decision"] == "need_info"
    assert any("not found" in p for p in state.values["problems"])


def test_b7_empty_message_needs_info_without_guessing(graph):
    """An empty message never reaches the model: read_enquiry returns the
    could-not-read result, so the case asks for information."""
    events = list(cases.stream_case(graph, "b7", "161", ""))
    state = graph.get_state(cases.thread_config("b7"))
    assert state.values["decision"] == "need_info"
    assert state.values["enquiry"].amount is None
    assert [node for node, _ in events] == ["intake", "validate", "need_info"]


# ---------- C: officer inbox and persistence ----------


def test_c1_inbox_lists_both_referred_cases(graph, prefilled):
    prefilled(graph, "b2", "161", 1200000, 60)
    prefilled(graph, "b4", "162", 200000, 24)
    prefilled(graph, "b1", "161", 500000, 36)
    assert cases.waiting_cases(graph) == ["b2", "b4"]
    summary = cases.waiting_summary(graph, "b4")
    assert summary["name"] == "agilan"
    assert summary["amount"] == 200000
    assert summary["tenure_months"] == 24
    assert summary["emi"] > 0
    assert summary["question"] == "Approve this loan?"
    assert "policy 1.3" in summary["reason"]


def test_c2_approve_with_comment(graph, prefilled):
    prefilled(graph, "b2", "161", 1200000, 60)
    values = cases.decide(graph, "b2", "approve", "test-manager", "Verified salary")
    assert values["decision"] == "approve"
    assert values["log"][-1].startswith("refer: human decided")
    assert values["decided_by"] == "test-manager"
    assert values["officer_comment"] == "Verified salary"
    assert "Verified salary" in values["reason"]
    assert "b2" not in cases.waiting_cases(graph)
    card = decision_card(values, cases.RATE_PERCENT)
    assert card["badge"] == "APPROVE"
    assert card["decided_by"] == "test-manager"


def test_c3_reject_by_officer(graph, prefilled):
    prefilled(graph, "b4", "162", 200000, 24)
    values = cases.decide(graph, "b4", "reject", "test-manager")
    assert values["decision"] == "reject"
    assert "Officer decided: reject" in values["reason"]
    with pytest.raises(ValueError):
        cases.decide(graph, "b4", "approve", "test-manager")


def test_c4_resume_after_restart_does_not_rerun_earlier_nodes(tmp_path, prefilled):
    db_file = tmp_path / "restart.db"
    first = sqlite_graph(db_file)
    prefilled(first, "c4", "162", 200000, 24)
    first.checkpointer.conn.close()  # the program stops

    second = sqlite_graph(db_file)  # a fresh start on the same file
    try:
        assert cases.waiting_cases(second) == ["c4"]
        values = cases.decide(second, "c4", "approve", "test-manager")
        steps = [line.split(":")[0] for line in values["log"]]
        assert steps == ["intake", "validate", "score", "refer"]
        nodes_run = [row["node"] for row in cases.history_rows(second, "c4")]
        assert nodes_run.count("validate") == 1
        assert nodes_run.count("score") == 1
    finally:
        second.checkpointer.conn.close()


def test_c5_cli_and_app_share_one_database(tmp_path, prefilled):
    """officer_app.py and the Streamlit app both open DB_PATH, and a case
    written through one graph object is listed by another on the same file."""
    import officer_app

    path = officer_app.graph.checkpointer.conn.execute(
        "PRAGMA database_list"
    ).fetchone()[2]
    assert path == str(DB_PATH)

    db_file = tmp_path / "shared.db"
    cli, app = sqlite_graph(db_file), sqlite_graph(db_file)
    try:
        prefilled(cli, "case-162", "162", 200000, 24)
        assert cases.waiting_cases(app) == ["case-162"]
    finally:
        cli.checkpointer.conn.close()
        app.checkpointer.conn.close()


def test_c6_case_viewer_data_for_a_finished_case(graph, prefilled):
    prefilled(graph, "b1", "161", 500000, 36)
    state = graph.get_state(cases.thread_config("b1"))
    assert state.next == ()
    assert state.values["log"][0] == "intake: pre-filled"
    rows = cases.history_rows(graph, "b1")
    assert [row["step"] for row in rows] == sorted(row["step"] for row in rows)
    assert rows[-1]["next"] == "-"
    assert rows[-1]["decision"] == "approve"


def test_c7_unknown_case_is_not_found(graph):
    values = cases.case_values(graph, "no-such-case")
    assert values == {}
    assert not cases.can_view(MANAGER_USER, values)


def test_c8_threads_are_independent(graph, prefilled):
    prefilled(graph, "one", "161", 500000, 36)
    prefilled(graph, "two", "161", None, None)
    one = cases.case_values(graph, "one")
    two = cases.case_values(graph, "two")
    assert one["decision"] == "approve"
    assert two["decision"] == "need_info"
    assert len(one["log"]) == 4
    assert len(two["log"]) == 3


def test_new_thread_id_format():
    from datetime import UTC, datetime

    moment = datetime(2026, 11, 3, 14, 5, 9, tzinfo=UTC)
    assert cases.new_thread_id(moment) == "case-20261103-140509"


# ---------- L: login and who may see what ----------


def test_l1_wrong_password_is_refused(accounts_in_db):
    user, error = login(accounts_in_db["customer"], "wrong-password", CUSTOMER)
    assert user is None
    assert error == BAD_LOGIN


def test_l1_role_must_match_the_account(accounts_in_db):
    user, _ = login(accounts_in_db["customer"], accounts_in_db["password"], MANAGER)
    assert user is None
    user, _ = login(accounts_in_db["manager"], accounts_in_db["password"], CUSTOMER)
    assert user is None


def test_l2_customer_and_manager_logins(accounts_in_db):
    customer, _ = login(
        accounts_in_db["customer"], accounts_in_db["password"], CUSTOMER
    )
    assert customer.customer_id == accounts_in_db["customer_id"]
    assert not customer.is_manager
    manager, _ = login(accounts_in_db["manager"], accounts_in_db["password"], MANAGER)
    assert manager.is_manager
    assert manager.customer_id is None


def test_l3_customers_only_see_themselves():
    customer = UserContext("vetri", CUSTOMER, 161)
    assert can_see_customer(customer, "161")
    assert can_see_customer(customer, " c161 ")
    assert not can_see_customer(customer, "162")
    assert can_see_customer(MANAGER_USER, "162")


def test_l5_customer_cannot_open_another_customers_case(graph, prefilled):
    prefilled(graph, "theirs", "162", 200000, 24)
    values = cases.case_values(graph, "theirs")
    assert not cases.can_view(UserContext("vetri", CUSTOMER, 161), values)
    assert cases.can_view(UserContext("agilan", CUSTOMER, 162), values)
    assert cases.visible_cases(graph, UserContext("vetri", CUSTOMER, 161)) == []


# ---------- A: the chat assistant (real model) ----------


@pytest.fixture(scope="module")
def agent():
    from policy_agent import build_agent

    return build_agent()


def chat(agent, question, user=MANAGER_USER):
    from policy_agent import answer_text, ask

    history, calls = ask(agent, [], question, user)
    return answer_text(history), [call["name"] for call in calls]


def emi(principal, rate, months):
    from tools import emi_calculator

    return emi_calculator.invoke(
        {"principal": principal, "annual_rate_percent": rate, "tenure_months": months}
    )


ELIGIBILITY = ["get_customer", "emi_calculator", "check_eligibility"]


@pytest.mark.llm
def test_b1_full_run_with_the_model(graph):
    """B1 end to end: the model reads the message in intake."""
    message = "Hi, I need a loan of 5 lakh rupees for 3 years to renovate my house."
    nodes = [node for node, _ in cases.stream_case(graph, "b1-llm", "161", message)]
    values = cases.case_values(graph, "b1-llm")
    assert nodes == ["intake", "validate", "score", "approve"]
    assert values["enquiry"].amount == 500000
    assert values["enquiry"].tenure_months == 36
    assert values["decision"] == "approve"


@pytest.mark.llm
def test_l3_agent_tool_denies_other_customers():
    from policy_agent import ACCESS_DENIED, get_customer

    runtime = SimpleNamespace(context=UserContext("vetri", CUSTOMER, 161))
    assert get_customer.func(customer_id="162", runtime=runtime) == ACCESS_DENIED
    assert get_customer.func(customer_id="161", runtime=runtime)["name"] == "vetri"


@pytest.mark.llm
def test_a1_emi(agent):
    answer, tools = chat(agent, "EMI for 3,00,000 at 10.5% for 24 months?")
    assert tools == ["emi_calculator"]
    assert f"{emi(300000, 10.5, 24):,.2f}" in answer


@pytest.mark.llm
def test_a2_emi_in_lakh_and_years(agent):
    answer, tools = chat(agent, "EMI for 5 lakh at 11% for 3 years?")
    assert tools == ["emi_calculator"]
    assert f"{emi(500000, 11, 36):,.2f}" in answer


@pytest.mark.llm
def test_a3_eligible_customer(agent):
    answer, tools = chat(
        agent, "Is customer 161 eligible for 5,00,000 at 11% for 36 months?"
    )
    assert tools == ELIGIBILITY
    assert "not eligible" not in answer.lower()
    assert "eligible" in answer.lower()


@pytest.mark.llm
def test_a4_not_eligible_lists_every_failure(agent):
    answer, tools = chat(
        agent, "Is customer 162 eligible for 6,00,000 at 11% for 24 months?"
    )
    lower = answer.lower()
    assert tools == ELIGIBILITY
    assert "not eligible" in lower
    assert "credit score 701" in lower
    assert "burden" in lower or "50%" in lower


@pytest.mark.llm
def test_a5_unknown_customer(agent):
    answer, tools = chat(agent, "Is C999 eligible for a loan?")
    assert "not found" in answer.lower()
    assert "999" in answer
    assert "check_eligibility" not in tools


@pytest.mark.llm
def test_a6_off_topic_declined(agent):
    from policy_agent import OFF_TOPIC

    answer, tools = chat(agent, "What is the capital of France?")
    assert tools == []
    assert OFF_TOPIC in answer
    assert "paris" not in answer.lower()


@pytest.mark.llm
def test_a7_missing_details_asked_for(agent):
    answer, tools = chat(agent, "Can I get a loan?")
    assert tools == []
    assert "customer id" in answer.lower()
    assert "?" in answer


POLICY_CASES = [
    ("What is the minimum age?", ["21"], "1.1"),
    ("What happens if my credit score is 680?", ["credit officer"], "1.3"),
    ("What is the processing fee on a 6,00,000 loan?", ["9,000"], "3.2"),
    ("Can I prepay after 8 months?", ["2"], "3.3"),
    ("What income proof does a self-employed applicant need?", ["itr"], "4.3"),
    ("Who approves a 12,00,000 loan?", ["senior manager"], "2.3"),
    ("How long until disbursal?", ["3 working days"], "5.1"),
    ("Can the money go to my friend's account?", ["own"], "5.2"),
    ("What interest rate will I get with a 750 score?", ["10.5", "16"], "3.1"),
]


@pytest.mark.llm
@pytest.mark.parametrize(
    ("question", "facts", "section"),
    POLICY_CASES,
    ids=["A8", "A9", "A10", "A11", "A12", "A13", "A14", "A15", "A17"],
)
def test_a8_to_a17_policy_answers_with_citation(agent, question, facts, section):
    answer, tools = chat(agent, question)
    assert "search_policy" in tools
    for fact in facts:
        assert fact in answer.lower()
    assert section in answer


@pytest.mark.llm
def test_a16_not_in_policy(agent):
    from policy_agent import NOT_FOUND

    answer, tools = chat(agent, "What is the policy on gold loans?")
    assert "search_policy" in tools
    assert NOT_FOUND in answer


@pytest.mark.llm
def test_a18_emi_and_processing_fee_use_both_tools(agent):
    answer, tools = chat(
        agent,
        "I want 6,00,000 for 36 months at 11%. What is the EMI and the processing fee?",
    )
    assert "emi_calculator" in tools
    assert "search_policy" in tools
    assert f"{emi(600000, 11, 36):,.2f}" in answer
    assert "9,000" in answer
    assert "3.2" in answer
