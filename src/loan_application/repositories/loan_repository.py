from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from loan_application.models import APPROVED, Loan


def add(db: Session, loan: Loan) -> None:
    db.add(loan)
    db.flush()


def get_by_id(db: Session, loan_id: int) -> Loan | None:
    return db.get(Loan, loan_id)


def count_approved_for_customer(db: Session, customer_id: int) -> int:
    stmt = select(func.count()).where(
        Loan.customer_id == customer_id, Loan.status == APPROVED
    )
    return db.execute(stmt).scalar_one()


def filtered(stmt: Select, customer_id: int | None, status: str | None) -> Select:
    if customer_id is not None:
        stmt = stmt.where(Loan.customer_id == customer_id)
    if status:
        stmt = stmt.where(Loan.status == status)
    return stmt


def list_for_customer(db: Session, customer_id: int, status: str | None) -> list[Loan]:
    stmt = filtered(select(Loan), customer_id, status)
    return list(db.scalars(stmt.order_by(Loan.id)))


def list_page(
    db: Session,
    customer_id: int | None,
    status: str | None,
    offset: int,
    limit: int,
) -> list[Loan]:
    """Oldest first; customer_id=None means every customer's loans."""
    stmt = filtered(select(Loan), customer_id, status)
    stmt = stmt.order_by(Loan.id).offset(offset).limit(limit)
    return list(db.scalars(stmt))


def count(db: Session, customer_id: int | None, status: str | None) -> int:
    stmt = filtered(select(func.count()).select_from(Loan), customer_id, status)
    return db.execute(stmt).scalar_one()
