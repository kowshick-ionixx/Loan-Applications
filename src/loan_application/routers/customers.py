from fastapi import APIRouter

from loan_application.db import DbSession
from loan_application.schemas.customer import CustomerCreate, CustomerOut
from loan_application.services import customer_service

router = APIRouter(prefix="/api/customers")


@router.post("", response_model=CustomerOut, status_code=201)
def create_customer(data: CustomerCreate, db: DbSession):
    return customer_service.create_customer(db, data)


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, db: DbSession):
    return customer_service.get_customer(db, customer_id)
