from fastapi import APIRouter

from loan_application.db import DbSession
from loan_application.dependencies import (
    CurrentUser,
    PositiveId,
    ProfileUser,
)
from loan_application.models import Customer
from loan_application.schemas.common import (
    PROTECTED_RESPONSES,
    error,
)
from loan_application.schemas.customer import (
    CustomerCreate,
    CustomerOut,
    CustomerSummary,
)
from loan_application.services import customer_service, loan_service

# EXTRA API imports - uncomment together with the EXTRA routes below.
# from typing import Annotated
# from fastapi import Query
# from loan_application.dependencies import OfficerUser
# from loan_application.schemas.common import MessageResponse
# from loan_application.schemas.customer import CustomerPage, CustomerUpdate

router = APIRouter(
    prefix="/api/customers", tags=["Customers"], responses=PROTECTED_RESPONSES
)
NOT_FOUND = {404: error("Customer not found")}


@router.post(
    "",
    response_model=CustomerOut,
    status_code=201,
    responses={409: error("Email already exists, or you already have a profile")},
)
def create_customer(data: CustomerCreate, db: DbSession, user: CurrentUser) -> Customer:
    """A CUSTOMER creates their own profile once, after registering; it is
    linked to their login. An OFFICER creates an unlinked profile (link a login
    with scripts/seed.py create_customer_user())."""
    return customer_service.create_customer(db, data, user)


# EXTRA API (not in Round 2 spec / plan up to Week 2 Tuesday) - uncomment to enable.
# @router.get("", response_model=CustomerPage)
# def list_customers(
#     db: DbSession,
#     user: OfficerUser,
#     page: Annotated[int, Query(ge=1)] = 1,
#     size: Annotated[int, Query(ge=1, le=100)] = 20,
# ) -> CustomerPage:
#     """Officers only. Newest last; `pages` is 0 when there are no customers."""
#     return customer_service.list_customers(db, page, size)
#
#
#

# EXTRA API (not in Round 2 spec / plan up to Week 2 Tuesday) - uncomment to enable.
# @router.get(
#     "/me",
#     response_model=CustomerOut,
#     responses={404: error("You do not have a customer profile")},
# )
# def get_my_customer(db: DbSession, user: CurrentUser) -> Customer:
#     return customer_service.get_own_customer(db, user)


@router.get("/{customer_id}", response_model=CustomerOut, responses=NOT_FOUND)
def get_customer(customer_id: PositiveId, db: DbSession, user: ProfileUser) -> Customer:
    return customer_service.get_customer_for_user(db, customer_id, user)


# EXTRA API (not in Round 2 spec / plan up to Week 2 Tuesday) - uncomment to enable.
# @router.patch(
#     "/{customer_id}",
#     response_model=CustomerOut,
#     responses={**NOT_FOUND, 409: error("Email already exists")},
# )
# def update_customer(
#     customer_id: PositiveId, data: CustomerUpdate, db: DbSession, user: ProfileUser
# ) -> Customer:
#     """Send only the fields to change. Customers may change name, phone and
#     address on their own profile; officers may change any field."""
#     return customer_service.update_customer(db, customer_id, data, user)
#
#
# @router.delete(
#     "/{customer_id}",
#     response_model=MessageResponse,
#     responses={**NOT_FOUND, 409: error("Customer has active (approved) loans")},
# )
# def delete_customer(
#     customer_id: PositiveId, db: DbSession, user: OfficerUser
# ) -> MessageResponse:
#     """Officers only. Rejected loan applications are deleted with the customer."""
#     customer_service.delete_customer(db, customer_id)
#     return MessageResponse(message="Customer deleted successfully")


@router.get(
    "/{customer_id}/summary", response_model=CustomerSummary, responses=NOT_FOUND
)
def get_customer_summary(
    customer_id: PositiveId, db: DbSession, user: ProfileUser
) -> CustomerSummary:
    return loan_service.get_customer_summary(db, customer_id, user)
