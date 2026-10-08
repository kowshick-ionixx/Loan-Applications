from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from loan_application.exceptions import AppError
from loan_application.models import Customer
from loan_application.repositories import customer_repository
from loan_application.schemas.customer import CustomerCreate


def commit_or_409(db: Session, error: str, message: str) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(409, error, message) from None


def create_customer(db: Session, data: CustomerCreate) -> Customer:
    customer = Customer(**data.model_dump())
    customer_repository.add(db, customer)
    commit_or_409(db, "DUPLICATE_EMAIL", "Email already exists")
    return customer


def get_customer(db: Session, customer_id: int) -> Customer:
    customer = customer_repository.get_by_id(db, customer_id)
    if customer is None:
        raise AppError(404, "NOT_FOUND", f"Customer with id {customer_id} not found")
    return customer


def update_customer(db: Session, customer_id: int, data: CustomerCreate) -> Customer:
    customer = get_customer(db, customer_id)
    for field, value in data.model_dump().items():
        setattr(customer, field, value)
    commit_or_409(db, "DUPLICATE_EMAIL", "Email already exists")
    return customer


def delete_customer(db: Session, customer_id: int) -> Customer:
    customer = get_customer(db, customer_id)
    customer_repository.delete(db, customer)
    commit_or_409(db, "CUSTOMER_HAS_LOANS", "Customer has loans, cannot delete")
    return customer
