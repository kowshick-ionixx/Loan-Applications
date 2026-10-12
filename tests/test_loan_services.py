from datetime import date
from decimal import Decimal

import pytest

from loan_application.exceptions import (
    CustomerNotFound,
    InvalidInputError,
    NotFoundError,
)
from loan_application.schemas.customer_schemas import CustomerIn
from loan_application.schemas.loan_schemas import LoanApplyIn
from loan_application.services import customer_services, loan_services


def make_customer_data(
    name="Mahesh",
    email="mahesh@example.com",
    phone="8720830079",
    dob=date(1990, 1, 1),
    income=Decimal("50000.00"),
):
    return CustomerIn(
        name=name,
        email=email,
        phone=phone,
        date_of_birth=dob,
        monthly_income=income,
    )


def make_loan_data(customer_id, amount="300000", tenure=36):
    return LoanApplyIn(
        customer_id=customer_id,
        amount=Decimal(amount),
        tenure_months=tenure,
    )


def create_customer(db_session):
    return customer_services.create_customer(
        db_session,
        make_customer_data(),
    )


def test_calculate_emi():
    emi = loan_services.calculate_emi(
        Decimal(300000),
        Decimal(12),
        36,
    )

    assert emi == Decimal("9964.29")


def test_apply_loan(db_session):
    customer = create_customer(db_session)

    loan = loan_services.apply_for_loan(
        db_session,
        make_loan_data(customer.id),
    )

    assert loan.id is not None
    assert loan.customer_id == customer.id
    assert loan.amount == Decimal("300000.00")
    assert loan.tenure_months == 36
    assert loan.interest_rate == Decimal("12.00")
    assert loan.emi == Decimal("9964.29")
    assert loan.status == "APPROVED"
    assert loan.rejection_reason is None


def test_reject_loan_for_age(db_session):
    customer = customer_services.create_customer(
        db_session,
        make_customer_data(
            name="Young Customer",
            email="young@example.com",
            phone="8720830080",
            dob=date(2010, 1, 1),
        ),
    )

    loan = loan_services.apply_for_loan(
        db_session,
        make_loan_data(customer.id, amount="10000", tenure=12),
    )

    assert loan.status == "REJECTED"
    assert loan.rejection_reason == "Age must be between 21 and 60"


def test_reject_loan_for_income(db_session):
    customer = customer_services.create_customer(
        db_session,
        make_customer_data(
            name="Low Income",
            email="lowincome@example.com",
            phone="8720830081",
            income=Decimal(10000),
        ),
    )

    loan = loan_services.apply_for_loan(
        db_session,
        make_loan_data(customer.id, amount="300000"),
    )

    assert loan.status == "REJECTED"
    assert loan.rejection_reason == ("Requested amount exceeds 20x monthly income")


def test_apply_loan_customer_not_found(db_session):
    with pytest.raises(CustomerNotFound):
        loan_services.apply_for_loan(
            db_session,
            make_loan_data(999),
        )


def test_get_loan(db_session):
    customer = create_customer(db_session)
    created = loan_services.apply_for_loan(
        db_session,
        make_loan_data(customer.id),
    )

    loan = loan_services.get_loan(db_session, created.id)

    assert loan.id == created.id
    assert loan.customer_id == customer.id


def test_get_missing_loan_raises(db_session):
    with pytest.raises(NotFoundError):
        loan_services.get_loan(db_session, 999)


def test_list_loans_for_customer(db_session):
    customer = create_customer(db_session)

    loan_services.apply_for_loan(
        db_session,
        make_loan_data(customer.id),
    )

    loans = loan_services.list_loans_for_customer(
        db_session,
        customer.id,
        "APPROVED",
    )

    assert len(loans) == 1
    assert loans[0].status == "APPROVED"


def test_list_loans_invalid_status(db_session):
    customer = create_customer(db_session)

    with pytest.raises(ValueError):
        loan_services.list_loans_for_customer(
            db_session,
            customer.id,
            "PENDING",
        )


def test_approve_loan(db_session):
    customer = create_customer(db_session)

    loan = loan_services.apply_for_loan(
        db_session,
        make_loan_data(customer.id),
    )

    updated = loan_services.approve_loan(db_session, loan.id)

    assert updated.status == "APPROVED"
    assert updated.emi is not None


def test_patch_loan_reject(db_session):
    customer = create_customer(db_session)

    loan = loan_services.apply_for_loan(
        db_session,
        make_loan_data(customer.id),
    )

    updated = loan_services.patch_loan(db_session, loan.id)

    assert updated.status == "REJECTED"
    assert updated.rejection_reason == "Rejected by administrator"


def test_delete_loan(db_session):
    customer = create_customer(db_session)

    loan = loan_services.apply_for_loan(
        db_session,
        make_loan_data(customer.id),
    )

    loan_services.delete_loan(db_session, loan.id)

    with pytest.raises(NotFoundError):
        loan_services.get_loan(db_session, loan.id)


def test_list_loans_invalid_status(db_session):
    customer = create_customer(db_session)

    with pytest.raises(InvalidInputError):
        loan_services.list_loans_for_customer(
            db_session,
            customer.id,
            "PENDING",
        )
