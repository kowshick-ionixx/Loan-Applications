from typing import Annotated

from fastapi import APIRouter, Query

from loan_application.db import DbSession
from loan_application.dependencies import PositiveId, ProfileUser
from loan_application.models import Loan
from loan_application.schemas.common import PROTECTED_RESPONSES, error
from loan_application.schemas.loan import LoanCreate, LoanOut, LoanPage, LoanStatus
from loan_application.services import loan_service

router = APIRouter(tags=["Loans"], responses=PROTECTED_RESPONSES)
LOAN_NOT_FOUND = {404: error("Loan not found")}
CUSTOMER_NOT_FOUND = {404: error("Customer not found")}


@router.post(
    "/api/loans",
    response_model=LoanOut,
    status_code=201,
    responses={**CUSTOMER_NOT_FOUND, 409: error("Customer was removed meanwhile")},
)
def apply_for_loan(data: LoanCreate, db: DbSession, user: ProfileUser) -> Loan:
    return loan_service.apply_for_loan(db, data, user)


@router.get("/api/loans", response_model=LoanPage)
def list_loans(
    db: DbSession,
    user: ProfileUser,
    status: LoanStatus | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> LoanPage:
    """Officers see every loan, customers only their own; oldest first.
    `pages` is 0 when nothing matches; a page past the end has no items."""
    return loan_service.list_loans(db, status, page, size, user)


@router.get("/api/loans/{loan_id}", response_model=LoanOut, responses=LOAN_NOT_FOUND)
def get_loan(loan_id: PositiveId, db: DbSession, user: ProfileUser) -> Loan:
    return loan_service.get_loan(db, loan_id, user)


@router.get(
    "/api/customers/{customer_id}/loans",
    response_model=list[LoanOut],
    responses=CUSTOMER_NOT_FOUND,
)
def list_customer_loans(
    customer_id: PositiveId,
    db: DbSession,
    user: ProfileUser,
    status: LoanStatus | None = None,
) -> list[Loan]:
    return loan_service.list_customer_loans(db, customer_id, status, user)
