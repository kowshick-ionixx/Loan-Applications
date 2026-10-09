from decimal import Decimal

import pytest

from loan_application.models import Loan
from loan_application.repositories import loan_repository
from loan_application.services.loan_service import (
    INTEREST_RATES,
    calculate_emi,
    check_eligibility,
)

AGE_REASON = "Age must be between 21 and 60"
INCOME_REASON = "Requested amount exceeds 20x monthly income"
ACTIVE_REASON = "Customer already has 2 active loans"


def test_emi_spec_example():
    assert calculate_emi(Decimal(300000), Decimal(12), 36) == Decimal("9964.29")


@pytest.mark.parametrize(
    "months, expected_emi",
    [
        (12, "8791.59"),
        (24, "4660.78"),
        (36, "3321.43"),
        (48, "2682.75"),
        (60, "2275.31"),
    ],
)
def test_emi_for_each_tenure(months, expected_emi):
    rate = INTEREST_RATES[months]
    assert calculate_emi(Decimal(100000), rate, months) == Decimal(expected_emi)


@pytest.mark.parametrize(
    "age, expected",
    [
        (20, AGE_REASON),
        (21, None),
        (60, None),
        (61, AGE_REASON),
    ],
)
def test_age_rule(make_customer, today, age, expected):
    customer = make_customer(age=age)
    assert check_eligibility(customer, Decimal(100000), 0, today) == expected


@pytest.mark.parametrize(
    "amount, expected",
    [
        ("1000000", None),
        ("1000001", INCOME_REASON),
    ],
)
def test_income_rule(make_customer, today, amount, expected):
    customer = make_customer(income="50000")
    assert check_eligibility(customer, Decimal(amount), 0, today) == expected


@pytest.mark.parametrize(
    "approved_count, expected",
    [
        (0, None),
        (1, None),
        (2, ACTIVE_REASON),
    ],
)
def test_active_loans_rule(make_customer, today, approved_count, expected):
    customer = make_customer()
    assert (
        check_eligibility(customer, Decimal(100000), approved_count, today) == expected
    )


def test_age_checked_before_income_and_active_loans(make_customer, today):
    customer = make_customer(age=20, income="10000")
    assert check_eligibility(customer, Decimal(5000000), 2, today) == AGE_REASON


def test_income_checked_before_active_loans(make_customer, today):
    customer = make_customer(income="10000")
    assert check_eligibility(customer, Decimal(5000000), 2, today) == INCOME_REASON


def test_count_approved_uses_test_database(db, make_customer, today):
    customer = make_customer()
    db.add(customer)
    db.flush()

    for status in ["APPROVED", "APPROVED", "REJECTED"]:
        db.add(
            Loan(
                customer_id=customer.id,
                amount=Decimal(100000),
                tenure_months=12,
                interest_rate=Decimal(10),
                emi=Decimal("8791.59") if status == "APPROVED" else None,
                status=status,
                rejection_reason=None if status == "APPROVED" else AGE_REASON,
                applied_on=today,
            )
        )
    db.flush()

    assert loan_repository.count_approved_for_customer(db, customer.id) == 2
