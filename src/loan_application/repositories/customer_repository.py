from sqlalchemy import select
from sqlalchemy.orm import Session

from loan_application.models import Customer


def add(db: Session, customer: Customer) -> None:
    db.add(customer)
    db.flush()


def get_by_id(db: Session, customer_id: int, lock: bool = False) -> Customer | None:
    """lock=True reads with SELECT ... FOR UPDATE: other transactions that lock
    or delete the same customer wait until this one commits or rolls back."""
    return db.get(Customer, customer_id, with_for_update=lock or None)


def get_by_email(db: Session, email: str) -> Customer | None:
    return db.scalar(select(Customer).where(Customer.email == email))
