"""Day 3: retrieval and cited policy answers. Expected sections and values are
found in the loaded policy text by keyword, never typed into the tests."""

import re

import oracle
import policy_index
import pytest
from support import (
    failure_label,
    find_section,
    mentions_amount,
    numbers_in,
    percentages,
)

NOT_FOUND = "I could not find this in the policy."


def first_percent(text: str) -> float:
    return percentages(text)[0]


def check_cited(chat, index, question, section, facts=(), check=None):
    """Ask, then assert search_policy ran, the section is cited and the facts
    are present. On failure the retrieved chunks and a cause label are shown."""
    answer, tools, _ = chat(question)
    retrieved = [hit.page_content for hit in index.similarity_search(question, k=3)]
    problems = []
    if "search_policy" not in tools:
        problems.append(f"search_policy not called (tools={tools})")
    if section not in answer:
        problems.append(f"section {section} not cited")
    problems += [
        f"missing {fact!r}" for fact in facts if fact.lower() not in answer.lower()
    ]
    if check is not None and not check(answer):
        problems.append("value check failed")
    if problems:
        label = failure_label(section, retrieved)
        chunks = "\n---\n".join(retrieved)
        pytest.fail(
            f"[{label}] {'; '.join(problems)}\nanswer: {answer}\nretrieved:\n{chunks}"
        )
    return answer


# ---------- unit ----------


def test_policy_has_the_sections_the_tests_use(policy_text):
    missing = []
    for keywords in [
        ("years of age",),
        ("referred",),
        ("Processing fee",),
        ("Prepayment",),
        ("self-employed", "ITR"),
        ("approval",),
        ("disbursed",),
        ("own bank account",),
        ("Interest rates",),
    ]:
        try:
            find_section(policy_text, *keywords)
        except AssertionError:
            missing.append(keywords)
    assert not missing, f"[DATA] no policy section contains: {missing}"


def test_d3_9_gold_is_not_in_the_policy(policy_text):
    assert "gold" not in policy_text.lower()


@pytest.mark.llm
def test_d3_u1_index_has_chunks(index):
    assert len(index.store) > 0


@pytest.mark.llm
def test_d3_u2_disbursal_is_the_top_hit(index, policy_text):
    section, _ = find_section(policy_text, "disbursed")
    top = index.similarity_search("How soon is the money paid out?", k=1)[0]
    assert section in top.page_content


@pytest.mark.llm
def test_d3_u3_changed_policy_changes_the_answers(tmp_path, monkeypatch, policy_text):
    section, text = find_section(policy_text, "disbursed")
    days = re.search(r"(\d+) working days", text).group(1)
    new_days = str(int(days) + 4)
    changed = policy_text.replace(f"{days} working days", f"{new_days} working days")
    copy = tmp_path / "loan_policy.txt"
    copy.write_text(changed, encoding="utf-8")
    monkeypatch.setattr(policy_index, "POLICY_FILE", copy)

    store = policy_index.build_index()
    top = store.similarity_search("How soon is the money paid out?", k=1)[0]
    assert f"{new_days} working days" in top.page_content

    from policy_qa import ask_policy

    result = ask_policy("How long until disbursal?", store=store)
    assert new_days in result.answer
    assert section in result.sections


# ---------- cited answers (llm) ----------


@pytest.mark.llm
def test_d3_1_minimum_age(chat, index, policy_text):
    section, text = find_section(policy_text, "years of age")
    youngest = min(int(n) for n in numbers_in(text))
    check_cited(chat, index, "What is the minimum age?", section, [str(youngest)])


@pytest.mark.llm
def test_d3_2_credit_score_in_refer_band(chat, index, policy_text, thresholds):
    section, _ = find_section(policy_text, "referred")
    score = (thresholds["refer_from"] + thresholds["min_credit"]) // 2
    check_cited(
        chat,
        index,
        f"What happens if my credit score is {score}?",
        section,
        ["credit officer"],
    )


@pytest.mark.llm
def test_d3_3_processing_fee(chat, index, policy_text, thresholds):
    section, text = find_section(policy_text, "Processing fee")
    principal = thresholds["min_amount"] * 12
    fee = first_percent(text) * principal / 100
    check_cited(
        chat,
        index,
        f"What is the processing fee on a {principal} loan?",
        section,
        check=lambda answer: mentions_amount(answer, fee),
    )


@pytest.mark.llm
def test_d3_4_prepayment(chat, index, policy_text):
    section, text = find_section(policy_text, "Prepayment")
    after, within = sorted(int(n) for n in re.findall(r"(\d+) months", text))[:2]
    months = (after + within) // 2
    charge = first_percent(text)
    check_cited(
        chat,
        index,
        f"Can I prepay after {months} months?",
        section,
        check=lambda answer: (
            charge in percentages(answer) or mentions_amount(answer, charge, 0)
        ),
    )


@pytest.mark.llm
def test_d3_5_self_employed_income_proof(chat, index, policy_text):
    section, _ = find_section(policy_text, "self-employed", "ITR")
    check_cited(
        chat,
        index,
        "What income proof does a self-employed applicant need?",
        section,
        ["ITR"],
    )


@pytest.mark.llm
def test_d3_6_high_value_approval(chat, index, policy_text, thresholds):
    section, _ = find_section(policy_text, "approval")
    amount = thresholds["high_value_limit"] + thresholds["min_amount"] * 4
    check_cited(
        chat, index, f"Who approves a loan of {amount}?", section, ["senior manager"]
    )


@pytest.mark.llm
def test_d3_7_disbursal_time(chat, index, policy_text):
    section, text = find_section(policy_text, "disbursed")
    days = re.search(r"(\d+) working days", text).group(1)
    check_cited(
        chat, index, "How long until disbursal?", section, [f"{days} working days"]
    )


@pytest.mark.llm
def test_d3_8_only_own_account(chat, index, policy_text):
    section, _ = find_section(policy_text, "own bank account")
    check_cited(
        chat, index, "Can the money go to my friend's account?", section, ["own"]
    )


@pytest.mark.llm
def test_d3_9_gold_loans_not_found(chat, policy_text):
    assert "gold" not in policy_text.lower()
    answer, tools, _ = chat("What is the policy on gold loans?")
    assert "search_policy" in tools
    assert NOT_FOUND in answer


@pytest.mark.llm
def test_d3_10_rate_range_only(chat, index, policy_text, thresholds):
    section, text = find_section(policy_text, "Interest rates")
    low, high = sorted(percentages(text))[:2]
    score = thresholds["min_credit"] + 30
    answer = check_cited(
        chat,
        index,
        f"What interest rate will I get with a {score} score?",
        section,
        check=lambda a: {low, high} <= set(percentages(a) + numbers_in(a)),
    )
    assert set(percentages(answer)) <= {low, high}, "an exact rate was invented"


@pytest.mark.llm
def test_d3_11_emi_and_processing_fee(chat, policy_text, thresholds):
    _, text = find_section(policy_text, "Processing fee")
    principal, n, rate = thresholds["min_amount"] * 12, 36, thresholds["rate"]
    answer, tools, _ = chat(
        f"I want {principal} for {n} months at {rate}%. What is the EMI and the processing fee?"
    )
    assert "search_policy" in tools
    assert "emi_calculator" in tools
    assert mentions_amount(answer, oracle.emi(principal, rate, n))
    assert mentions_amount(answer, first_percent(text) * principal / 100)
