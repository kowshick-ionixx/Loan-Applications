from sqlalchemy import func, select
from sqlalchemy.orm import Session

from loan_application.tables import Customer


def get_by_id(db: Session, customer_id: int) -> Customer | None:
    return db.get(Customer, customer_id)


def email_exists(db: Session, email: str) -> bool:
    normalized_email = email.strip().lower()

    query = select(Customer.id).where(
        func.lower(func.trim(Customer.email)) == normalized_email
    )

    return db.scalar(query) is not None


def email_taken_by_other(db: Session, email: str, customer_id: int) -> bool:
    stmt = select(Customer.id).where(
        Customer.email == email, Customer.id != customer_id
    )
    return db.scalar(stmt) is not None


def add(db: Session, customer: Customer) -> None:
    db.add(customer)


def delete(db: Session, customer: Customer) -> None:
    db.delete(customer)
