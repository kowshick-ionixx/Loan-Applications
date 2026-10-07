from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from loan_application.exceptions import AppError
from loan_application.models import Customer
from loan_application.repositories import customer_repository
from loan_application.schemas.customer import CustomerCreate


def create_customer(db: Session, data: CustomerCreate) -> Customer:
    customer = Customer(**data.model_dump())
    customer_repository.add(db, customer)
    try:
        db.commit()
    except IntegrityError as exc:  # the email column is unique
        db.rollback()
        raise AppError(409, "DUPLICATE_EMAIL", "Email already exists") from exc
    return customer


def get_customer(db: Session, customer_id: int) -> Customer:
    customer = customer_repository.get_by_id(db, customer_id)
    if customer is None:
        raise AppError(404, "NOT_FOUND", f"Customer with id {customer_id} not found")
    return customer
