from fastapi import APIRouter

from loan_application.db import DbSession
from loan_application.dependencies import CurrentUser, PositiveId, ProfileUser
from loan_application.models import Customer
from loan_application.schemas.common import PROTECTED_RESPONSES, error
from loan_application.schemas.customer import (
    CreditScoreCheck,
    CustomerCreate,
    CustomerOut,
    CustomerSummary,
)
from loan_application.services import customer_service, loan_service

router = APIRouter(
    prefix="/api/customers", tags=["Customers"], responses=PROTECTED_RESPONSES
)
NOT_FOUND = {404: error("Customer not found")}


@router.post(
    "",
    response_model=CustomerOut,
    status_code=201,
    responses={
        400: error("`username` is not a CUSTOMER login"),
        404: error("No user with that `username`"),
        409: error("Email already exists, or the login already has a profile"),
    },
)
def create_customer(data: CustomerCreate, db: DbSession, user: CurrentUser) -> Customer:
    """A CUSTOMER creates their own profile once, after registering; it is
    linked to their login. An OFFICER sends `username` to create the profile
    for that registered CUSTOMER login and link it; without `username` the
    profile is created unlinked."""
    return customer_service.create_customer(db, data, user)


@router.get("/{customer_id}", response_model=CustomerOut, responses=NOT_FOUND)
def get_customer(customer_id: PositiveId, db: DbSession, user: ProfileUser) -> Customer:
    return customer_service.get_customer_for_user(db, customer_id, user)


@router.get(
    "/{customer_id}/summary", response_model=CustomerSummary, responses=NOT_FOUND
)
def get_customer_summary(
    customer_id: PositiveId, db: DbSession, user: ProfileUser
) -> CustomerSummary:
    return loan_service.get_customer_summary(db, customer_id, user)


@router.get(
    "/{customer_id}/credit-score",
    response_model=CreditScoreCheck,
    responses=NOT_FOUND,
)
def get_credit_score(
    customer_id: PositiveId, db: DbSession, user: ProfileUser
) -> CreditScoreCheck:
    """Shows the customer's credit score and whether it meets the minimum (715)
    needed for loan approval. Only the credit-score rule is checked: age,
    income and active loans still apply when a loan is requested."""
    return loan_service.check_credit_score(db, customer_id, user)
