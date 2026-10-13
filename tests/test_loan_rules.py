from datetime import date
from decimal import Decimal

import pytest

from loan_application.models import Customer
from loan_application.services.loan_service import (
    INTEREST_RATES,
    calculate_emi,
    check_eligibility,
    get_risk_band,
)

TODAY = date(2026, 10, 8)
AGE_REASON = "Age must be between 21 and 60"
INCOME_REASON = "Requested amount exceeds 20x monthly income"
ACTIVE_REASON = "Customer already has 2 active loans"


def make_customer(age: int = 30, income: str = "50000") -> Customer:
    dob = date(TODAY.year - age, TODAY.month, TODAY.day)
    return Customer(date_of_birth=dob, monthly_income=Decimal(income))


def test_emi_spec_example():
    assert calculate_emi(Decimal(300000), Decimal(12), 36) == Decimal("9964.29")


@pytest.mark.parametrize(
    ("months", "rate", "expected_emi"),
    [
        (12, 10, "8791.59"),
        (24, 11, "4660.78"),
        (36, 12, "3321.43"),
        (48, 13, "2682.75"),
        (60, 13, "2275.31"),
    ],
)
def test_rate_and_emi_for_each_tenure(months, rate, expected_emi):
    assert INTEREST_RATES[months] == rate
    emi = calculate_emi(Decimal(100000), INTEREST_RATES[months], months)
    assert emi == Decimal(expected_emi)


@pytest.mark.parametrize(
    ("age", "expected"),
    [(19, AGE_REASON), (20, AGE_REASON), (21, None), (60, None), (61, AGE_REASON)],
)
def test_age_rule(age, expected):
    customer = make_customer(age=age)
    assert check_eligibility(customer, Decimal(100000), 0, TODAY) == expected


@pytest.mark.parametrize(
    ("amount", "income", "expected"),
    [
        ("1000000", "50000", None),
        ("1000001", "50000", INCOME_REASON),
        ("1000000", "40000", INCOME_REASON),
    ],
)
def test_income_rule(amount, income, expected):
    customer = make_customer(income=income)
    assert check_eligibility(customer, Decimal(amount), 0, TODAY) == expected


@pytest.mark.parametrize(
    ("approved_count", "expected"), [(0, None), (1, None), (2, ACTIVE_REASON)]
)
def test_active_loans_rule(approved_count, expected):
    customer = make_customer()
    result = check_eligibility(customer, Decimal(100000), approved_count, TODAY)
    assert result == expected


def test_first_failing_rule_wins():
    young_and_poor = make_customer(age=20, income="10000")
    assert check_eligibility(young_and_poor, Decimal(5000000), 2, TODAY) == AGE_REASON
    poor = make_customer(income="10000")
    assert check_eligibility(poor, Decimal(5000000), 2, TODAY) == INCOME_REASON


@pytest.mark.parametrize(
    ("ratio", "band"),
    [
        ("0", "LOW"),
        ("29.99", "LOW"),
        ("30", "MEDIUM"),
        ("50", "MEDIUM"),
        ("50.01", "HIGH"),
    ],
)
def test_risk_band(ratio, band):
    assert get_risk_band(Decimal(ratio)) == band
