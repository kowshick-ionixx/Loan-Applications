from sqlalchemy import func, select
from sqlalchemy.orm import Session

from loan_application.models import Customer


def add(db: Session, customer: Customer) -> None:
    db.add(customer)
    db.flush()


def get_by_id(db: Session, customer_id: int) -> Customer | None:
    return db.get(Customer, customer_id)


def delete(db: Session, customer: Customer) -> None:
    db.delete(customer)
    db.flush()


def get_by_email(db: Session, email: str) -> Customer | None:
    return db.scalar(select(Customer).where(Customer.email == email))


def list_page(db: Session, offset: int, limit: int) -> list[Customer]:
    stmt = select(Customer).order_by(Customer.id).offset(offset).limit(limit)
    return list(db.scalars(stmt))


def count(db: Session) -> int:
    return db.execute(select(func.count()).select_from(Customer)).scalar_one()
