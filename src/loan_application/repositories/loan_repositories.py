from sqlalchemy import func, select
from sqlalchemy.orm import Session
from loan_application.tables import Loan




def count_approved_for_customer(db: Session, customer_id: int) -> int:
    stmt = (
        select(func.count())
        .select_from(Loan)
        .where(Loan.customer_id == customer_id, Loan.status == "APPROVED")
    )
    return db.scalar(stmt)


def add(db: Session, loan: Loan) -> None:
    db.add(loan)


def get_by_id(db: Session, loan_id: int) -> Loan | None:
    return db.get(Loan, loan_id)


def list_for_customer(
    db: Session, customer_id: int, status: str | None = None
) -> list[Loan]:
    stmt = select(Loan).where(Loan.customer_id == customer_id)
    if status is not None:
        stmt = stmt.where(Loan.status == status)
    stmt = stmt.order_by(Loan.applied_on.desc(), Loan.id.desc())  # newest first
    return list(db.scalars(stmt))


def summary_for_customer(db: Session, customer_id: int):
    """One query: (total, approved, rejected, approved_amount, approved_emi)."""
    approved = Loan.status == "APPROVED"
    stmt = select(
        func.count(Loan.id),  # total_applications
        func.count(Loan.id).filter(approved),  # approved_count
        func.count(Loan.id).filter(Loan.status == "REJECTED"),  # rejected_count
        func.coalesce(func.sum(Loan.amount).filter(approved), 0),  # approved amount
        func.coalesce(func.sum(Loan.emi).filter(approved), 0),  # approved EMI
    ).where(Loan.customer_id == customer_id)
    return db.execute(stmt).one()


def count_approved_for_customer(
    db: Session,
    customer_id: int,
) -> int:
    statement = (
        select(func.count())
        .select_from(Loan)
        .where(
            Loan.customer_id == customer_id,
            Loan.status == "APPROVED",
        )
    )
    return db.scalar(statement) or 0


def delete(db: Session, loan: Loan) -> None:
    db.delete(loan)




def list_by_customer(db: Session, customer_id: int, status: str | None = None) -> list[Loan]:
    stmt = select(Loan).where(Loan.customer_id == customer_id)
    if status is not None:
        stmt = stmt.where(Loan.status == status)
    stmt = stmt.order_by(Loan.applied_on.desc(), Loan.id.desc())
    return list(db.scalars(stmt))