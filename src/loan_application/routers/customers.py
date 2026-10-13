from fastapi import APIRouter

from loan_application.db import DbSession
from loan_application.dependencies import (
    CurrentUser,
    PositiveId,
    ProfileUser,
)
from loan_application.models import Customer
from loan_application.schemas.customer import (
    CustomerCreate,
    CustomerOut,
    CustomerSummary,
)
from loan_application.services import customer_service, loan_service

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.post("", response_model=CustomerOut, status_code=201)
def create_customer(data: CustomerCreate, db: DbSession, user: CurrentUser) -> Customer:
    return customer_service.create_customer(db, data, user)


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: PositiveId, db: DbSession, user: ProfileUser) -> Customer:
    return customer_service.get_customer_for_user(db, customer_id, user)


@router.get("/{customer_id}/summary", response_model=CustomerSummary)
def get_customer_summary(
    customer_id: PositiveId, db: DbSession, user: ProfileUser
) -> CustomerSummary:
    return loan_service.get_customer_summary(db, customer_id, user)
