import pytest
from loan_application.services import customer_services
from loan_application.schemas import CustomerIn
from loan_application.exceptions import CustomerNotFound   # use your real exception name
from datetime import date
from decimal import Decimal
 
 
def make_customer_data():
    # Fill in the fields your CustomerIn schema actually requires
    return CustomerIn(name="mahesh", email="mahesh@example.com",phone="8720830079",date_of_birth=date(1990, 1, 1),monthly_income=Decimal("50000.00"),)
 
 
def test_create_customer(db_session):
    customer = customer_services.create_customer(db_session, make_customer_data())
    assert customer.id is not None
    assert customer.name == "mahesh"
    assert customer.phone == "8720830079"
    assert customer.date_of_birth == date(1990, 1, 1)
    assert customer.monthly_income == Decimal("50000.00")
 
 
def test_update_customer(db_session):
    customer = customer_services.create_customer(db_session, make_customer_data())
    updated = customer_services.update_customer(
        db_session, customer.id, CustomerIn(name="madhav", email="madhav@example.com",phone="9876543210",
            date_of_birth=date(1995, 5, 15),
            monthly_income=Decimal("65000.00"),
        )
    )
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