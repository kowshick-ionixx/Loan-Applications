from fastapi import APIRouter

from loan_application.db import DbSession
from loan_application.dependencies import PositiveId, ProfileUser
from loan_application.models import Loan
from loan_application.schemas.loan import LoanCreate, LoanOut, LoanStatus
from loan_application.services import loan_service

router = APIRouter(tags=["loans"])


@router.post("/api/loans", response_model=LoanOut, status_code=201)
def apply_for_loan(data: LoanCreate, db: DbSession, user: ProfileUser) -> Loan:
    return loan_service.apply_for_loan(db, data, user)


@router.get("/api/loans/{loan_id}", response_model=LoanOut)
def get_loan(loan_id: PositiveId, db: DbSession, user: ProfileUser) -> Loan:
    return loan_service.get_loan(db, loan_id, user)


@router.get("/api/customers/{customer_id}/loans", response_model=list[LoanOut])
def list_customer_loans(
    customer_id: PositiveId,
    db: DbSession,
    user: ProfileUser,
    status: LoanStatus | None = None,
) -> list[Loan]:
    return loan_service.list_customer_loans(db, customer_id, status, user)
