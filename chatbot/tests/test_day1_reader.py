"""Day 1: the enquiry reader. Inputs are messages (not customer records)."""

import enquiry_reader
import pytest
from enquiry_reader import CORE_FIELDS, LoanEnquiry, could_not_read, read_enquiry
from langchain_core.runnables import RunnableLambda

READS = [
    (
        "D1-1",
        "I need a loan of 5 lakh rupees for 3 years to renovate my house",
        500000,
        36,
    ),
    ("D1-2", "Rs 12,00,000 personal loan, repayment over 60 months", 1200000, 60),
    ("D1-3", "around 2 lakhs, can repay in 18 months", 200000, 18),
    ("D1-5", "Business expansion loan, 25L, 5 years", 2500000, 60),
]


@pytest.mark.llm
@pytest.mark.parametrize(
    ("case", "text", "amount", "tenure"), READS, ids=[r[0] for r in READS]
)
def test_amount_and_tenure_read(case, text, amount, tenure):
    result = read_enquiry(text)
    assert result.amount == amount
    assert result.tenure_months == tenure


@pytest.mark.llm
def test_d1_4_missing_amount_not_guessed():
    result = read_enquiry("loan for buying a two-wheeler. My name is Priya.")
    assert result.amount is None
    assert result.tenure_months is None
    assert "amount" in result.missing_fields


def test_d1_6_empty_text_gives_could_not_read():
    assert read_enquiry("") == could_not_read()


@pytest.mark.llm
def test_d1_7_no_values_invented():
    result = read_enquiry("hello")
    assert result.amount is None
    assert result.tenure_months is None
    assert result.confidence == "low"


@pytest.mark.llm
def test_d1_8_return_type():
    result = read_enquiry(READS[0][1])
    assert type(result) is LoanEnquiry
    assert result.confidence in {"high", "medium", "low"}


@pytest.mark.llm
def test_d1_9_batch_keeps_input_order():
    texts = [text for _, text, _, _ in READS] + ["hello"]
    results = RunnableLambda(read_enquiry).batch(texts)
    assert len(results) == 5
    assert [r.amount for r in results[:4]] == [amount for _, _, amount, _ in READS]


class FlakyChain:
    """Stands in for the model chain: fails `failures` times, then answers."""

    def __init__(self, failures: int):
        self.failures = failures
        self.calls = 0

    def invoke(self, _inputs):
        self.calls += 1
        if self.calls <= self.failures:
            raise RuntimeError("model unavailable")
        return LoanEnquiry(
            amount=500000,
            tenure_months=36,
            customer_name="Test",
            purpose="test",
            confidence="high",
        )


def test_d1_10_one_failure_is_retried(monkeypatch):
    chain = FlakyChain(failures=1)
    monkeypatch.setattr(enquiry_reader, "chain", chain)
    result = read_enquiry("any message")
    assert chain.calls == 2
    assert result.amount == 500000


def test_d1_11_two_failures_give_clean_fallback(monkeypatch):
    chain = FlakyChain(failures=2)
    monkeypatch.setattr(enquiry_reader, "chain", chain)
    result = read_enquiry("any message")
    assert chain.calls == 2
    assert result == could_not_read()
    assert set(result.missing_fields) == set(CORE_FIELDS)
