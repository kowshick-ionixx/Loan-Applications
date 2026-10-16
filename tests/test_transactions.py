"""The transaction boundary in the service layer: one commit per operation,
a full rollback on any error, and the customer row lock on loan applications."""

import threading
from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import delete, event, select
from sqlalchemy.exc import IntegrityError

from loan_application.db import SessionLocal, transaction
from loan_application.exceptions import AppError
from loan_application.models import APPROVED, Customer, Loan, User, UserRole
from loan_application.repositories import customer_repository
from loan_application.schemas.loan import LoanCreate
from loan_application.services import loan_service

OFFICER = User(username="tx-officer", role=UserRole.OFFICER)


def new_customer(email="tx@example.com"):
    return Customer(
        name="Tx Customer",
        email=email,
        phone="9876543210",
        date_of_birth=date(1990, 5, 15),
        monthly_income=Decimal(50000),
    )


def approved_loan(customer_id):
    return Loan(
        customer_id=customer_id,
        amount=Decimal(100000),
        tenure_months=12,
        interest_rate=Decimal(10),
        emi=Decimal("8791.59"),
        status=APPROVED,
        applied_on=datetime.now().astimezone().date(),
    )


def test_any_error_rolls_back_the_whole_unit(db):
    with pytest.raises(ValueError), transaction(db):
        db.add(new_customer())
        db.flush()
        raise ValueError("boom")
    assert db.scalar(select(Customer).where(Customer.email == "tx@example.com")) is None


def test_integrity_error_becomes_409_and_rolls_back(db):
    db.add(new_customer())
    db.flush()
    with pytest.raises(AppError) as caught, transaction(db, "DUPLICATE_EMAIL", "taken"):
        db.add(new_customer(email="other@example.com"))
        db.add(new_customer())
        db.flush()
    assert (caught.value.status_code, caught.value.error) == (409, "DUPLICATE_EMAIL")
    assert (
        db.scalar(select(Customer).where(Customer.email == "other@example.com")) is None
    )


def test_integrity_error_without_code_is_reraised(db):
    db.add(new_customer())
    db.flush()
    with pytest.raises(IntegrityError), transaction(db):
        db.add(new_customer())
        db.flush()


def test_loan_application_locks_the_customer_row(db):
    customer = new_customer()
    db.add(customer)
    db.flush()
    statements = []
    event.listen(
        db.connection(),
        "before_cursor_execute",
        lambda conn, cursor, sql, *args: statements.append(sql),
    )
    data = LoanCreate(customer_id=customer.id, amount=100000, tenure_months=12)
    loan_service.apply_for_loan(db, data, OFFICER)
    locks = [s for s in statements if "FROM customers" in s and "FOR UPDATE" in s]
    assert locks, statements


@pytest.fixture
def committed_customer():
    """Real, committed rows: the race below needs two separate connections,
    so it cannot use the rolled-back test transaction."""
    with SessionLocal() as session:
        customer = new_customer(email="race@example.com")
        session.add(customer)
        session.flush()
        session.add(approved_loan(customer.id))
        session.commit()
        customer_id = customer.id
    yield customer_id
    with SessionLocal() as session:
        session.execute(delete(Loan).where(Loan.customer_id == customer_id))
        session.execute(delete(Customer).where(Customer.id == customer_id))
        session.commit()


def test_second_application_waits_for_the_first(committed_customer):
    """The customer already has 1 approved loan, so only 1 more may be approved.
    Application A is mid-transaction (row locked, 2nd approval inserted, not yet
    committed). Application B must wait for it and then be rejected; without
    the lock B would count only 1 approved loan and be approved too."""
    data = LoanCreate(customer_id=committed_customer, amount=100000, tenure_months=12)
    results, errors = [], []

    def apply_b():
        try:
            with SessionLocal() as session:
                results.append(
                    loan_service.apply_for_loan(session, data, OFFICER).status
                )
        except Exception as exc:  # noqa: BLE001 - surfaced by the assert below
            errors.append(exc)

    with SessionLocal() as session_a:
        customer_repository.get_by_id(session_a, committed_customer, lock=True)
        session_a.add(approved_loan(committed_customer))
        session_a.flush()

        b = threading.Thread(target=apply_b)
        b.start()
        b.join(timeout=1)
        assert b.is_alive(), f"B did not wait for A's lock: {results or errors}"
        session_a.commit()

    b.join(timeout=30)
    assert not errors, errors
    assert results == ["REJECTED"]
