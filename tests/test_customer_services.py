from datetime import date
from decimal import Decimal

import pytest

from loan_application.exceptions import CustomerNotFound  # use your real exception name
from loan_application.schemas import CustomerIn
from loan_application.services import customer_services


def make_customer_data(**overrides):
    # Fill in the fields your CustomerIn schema actually requires
    default_data = {
        "name": "mahesh",
        "email": "mahesh@example.com",
        "phone": "8720830079",
        "date_of_birth": date(1990, 1, 1),
        "monthly_income": Decimal("50000.00"),
    }
    default_data.update(overrides)
    return CustomerIn(**default_data)


def test_create_customer(db_session):
    customer = customer_services.create_customer(db_session, make_customer_data())
    assert customer.id is not None
    assert customer.name == "mahesh"
    assert customer.phone == "8720830079"
    assert customer.date_of_birth == date(1990, 1, 1)
    assert customer.monthly_income == Decimal("50000.00")


def test_update_customer(db_session):
    customer = customer_services.create_customer(
        db_session,
        make_customer_data(name="vetri", email="vetri@example.com"),
    )
    old_name = customer.name
    old_email = customer.email
    old_phone = customer.phone
    old_income = customer.monthly_income
    print("BEFORE:", old_name, old_email, old_phone, old_income)
    updated = customer_services.update_customer(
        db_session,
        customer.id,
        CustomerIn(
            name="madhav",
            email="madhav@example.com",
            phone="9876543210",
            date_of_birth=date(1995, 5, 15),
            monthly_income=Decimal("65000.00"),
        ),
    )
    print("AFTER :", updated.name, updated.email, updated.phone, updated.monthly_income)
    assert updated.name == "madhav"
    assert updated.email == "madhav@example.com"
    assert updated.phone == "9876543210"
    assert updated.date_of_birth == date(1995, 5, 15)
    assert updated.monthly_income == Decimal("65000.00")


def test_delete_customer(db_session):
    customer = customer_services.create_customer(db_session, make_customer_data())
    customer_services.delete_customer(db_session, customer.id)
    with pytest.raises(CustomerNotFound):
        customer_services.get_customer(db_session, customer.id)


def test_get_missing_customer_raises(db_session):
    with pytest.raises(CustomerNotFound):
        customer_services.get_customer(db_session, 999999)
