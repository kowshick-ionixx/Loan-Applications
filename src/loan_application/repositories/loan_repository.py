from sqlalchemy import func, select
from sqlalchemy.orm import Session

from loan_application.models import Loan


def add(db: Session, loan: Loan) -> None:
    db.add(loan)


def get_by_id(db: Session, loan_id: int) -> Loan | None:
    return db.get(Loan, loan_id)


def count_approved_for_customer(db: Session, customer_id: int) -> int:
    stmt = select(func.count()).where(
        Loan.customer_id == customer_id, Loan.status == "APPROVED"
    )
    return db.scalar(stmt)


def list_for_customer(db: Session, customer_id: int, status: str | None) -> list[Loan]:
    stmt = select(Loan).where(Loan.customer_id == customer_id)
    if status:
        stmt = stmt.where(Loan.status == status)
    return list(db.scalars(stmt.order_by(Loan.id.desc())))
