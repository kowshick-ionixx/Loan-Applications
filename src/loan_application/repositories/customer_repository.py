from sqlalchemy.orm import Session

from loan_application.models import Customer


def add(db: Session, customer: Customer) -> None:
    db.add(customer)


def get_by_id(db: Session, customer_id: int) -> Customer | None:
    return db.get(Customer, customer_id)


def delete(db: Session, customer: Customer) -> None:
    db.delete(customer)
