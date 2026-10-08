from typing import Annotated

from fastapi import APIRouter, Path

from loan_application.db import MAX_ID, DbSession
from loan_application.schemas.customer import (
    CustomerCreate,
    CustomerOut,
    CustomerSummary,
)
from loan_application.services import customer_service, loan_service

router = APIRouter(prefix="/api/customers", tags=["customers"])

CustomerId = Annotated[int, Path(gt=0, le=MAX_ID)]


@router.post("", response_model=CustomerOut, status_code=201)
def create_customer(data: CustomerCreate, db: DbSession):
    return customer_service.create_customer(db, data)


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: CustomerId, db: DbSession):
    return customer_service.get_customer(db, customer_id)


@router.get("/{customer_id}/summary", response_model=CustomerSummary)
def get_customer_summary(customer_id: CustomerId, db: DbSession):
    return loan_service.get_customer_summary(db, customer_id)


@router.put("/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: CustomerId, data: CustomerCreate, db: DbSession):
    return customer_service.update_customer(db, customer_id, data)


@router.delete("/{customer_id}", response_model=CustomerOut)
def delete_customer(customer_id: CustomerId, db: DbSession):
    return customer_service.delete_customer(db, customer_id)
