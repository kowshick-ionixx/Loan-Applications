from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from loan_application.exceptions import AppError
from loan_application.models import Customer
from loan_application.repositories import customer_repository
from loan_application.schemas.customer import CustomerCreate


def create_customer(db: Session, data: CustomerCreate) -> Customer:
    customer = Customer(
        name=data.name,
        email=data.email,
        phone=data.phone,
        date_of_birth=data.date_of_birth,
        monthly_income=data.monthly_income,
    )
    customer_repository.add(db, customer)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(409, "DUPLICATE_EMAIL", "Email already exists")
    return customer


def get_customer(db: Session, customer_id: int) -> Customer:
    customer = customer_repository.get_by_id(db, customer_id)
    if customer is None:
        raise AppError(404, "NOT_FOUND", f"Customer with id {customer_id} not found")
    return customer


def update_customer(db: Session, customer_id: int, data: CustomerCreate) -> Customer:
    customer = get_customer(db, customer_id)
    customer.name = data.name
    customer.email = data.email
    customer.phone = data.phone
    customer.date_of_birth = data.date_of_birth
    customer.monthly_income = data.monthly_income
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(409, "DUPLICATE_EMAIL", "Email already exists")
    return customer


def delete_customer(db: Session, customer_id: int) -> Customer:
    customer = get_customer(db, customer_id)
    customer_repository.delete(db, customer)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(409, "CUSTOMER_HAS_LOANS", "Customer has loans, cannot delete")
    return customer
