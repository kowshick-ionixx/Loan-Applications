from typing import Annotated

from fastapi import APIRouter, Path, Query

from loan_application.db import MAX_ID, DbSession
from loan_application.schemas.loan import LoanCreate, LoanOut, LoanStatus
from loan_application.services import loan_service

router = APIRouter(tags=["loans"])

PositiveId = Annotated[int, Path(gt=0, le=MAX_ID)]


@router.post("/api/loans", response_model=LoanOut, status_code=201)
def apply_for_loan(data: LoanCreate, db: DbSession):
    return loan_service.apply_for_loan(db, data)


@router.get("/api/loans/{loan_id}", response_model=LoanOut)
def get_loan(loan_id: PositiveId, db: DbSession):
    return loan_service.get_loan(db, loan_id)


@router.get("/api/customers/{customer_id}/loans", response_model=list[LoanOut])
def list_customer_loans(
    customer_id: PositiveId,
    db: DbSession,
    status: Annotated[LoanStatus | None, Query()] = None,
):
    return loan_service.list_customer_loans(db, customer_id, status)
