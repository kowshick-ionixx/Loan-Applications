from fastapi import APIRouter

from loan_application.db import DbSession
from loan_application.dependencies import PositiveId, ProfileUser
from loan_application.models import Loan
from loan_application.schemas.common import (
    PROTECTED_RESPONSES,
    error,
)
from loan_application.schemas.loan import LoanCreate, LoanOut, LoanStatus
from loan_application.services import loan_service

# EXTRA API imports - uncomment together with the EXTRA routes below.
# from loan_application.dependencies import OfficerUser
# from loan_application.schemas.common import MessageResponse

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


# EXTRA API (not in Round 2 spec / plan up to Week 2 Tuesday) - uncomment to enable.
# @router.get("/api/loans", response_model=list[LoanOut])
# def list_loans(
#     db: DbSession, user: ProfileUser, status: LoanStatus | None = None
# ) -> list[Loan]:
#     return loan_service.list_loans(db, status, user)


@router.get("/api/loans/{loan_id}", response_model=LoanOut, responses=LOAN_NOT_FOUND)
def get_loan(loan_id: PositiveId, db: DbSession, user: ProfileUser) -> Loan:
    return loan_service.get_loan(db, loan_id, user)


# EXTRA API (not in Round 2 spec / plan up to Week 2 Tuesday) - uncomment to enable.
# @router.delete(
#     "/api/loans/{loan_id}", response_model=MessageResponse, responses=LOAN_NOT_FOUND
# )
# def delete_loan(
#     loan_id: PositiveId, db: DbSession, user: OfficerUser
# ) -> MessageResponse:
#     loan_service.delete_loan(db, loan_id, user)
#     return MessageResponse(message="Loan deleted successfully")


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
