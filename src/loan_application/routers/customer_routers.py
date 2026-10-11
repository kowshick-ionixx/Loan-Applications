from loan_application.schemas.customer_schemas import CustomerIn, CustomerOut, CustomerSummaryOut
from loan_application.services import customer_services, loan_services


from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from loan_application.db import get_db
from loan_application.schemas.customer_schemas import CustomerIn, CustomerOut, CustomerSummaryOut, MessageOut
from loan_application.services import customer_services

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.post("/", response_model=CustomerOut, status_code=201)
def add_customer(data: CustomerIn, db: Session = Depends(get_db)):
    return customer_services.create_customer(db, data)


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    return customer_services.get_customer(db, customer_id)


@router.put("/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: int, data: CustomerIn, db: Session = Depends(get_db)):
    return customer_services.update_customer(db, customer_id, data)


@router.delete("/{customer_id}", response_model=MessageOut, status_code=200)
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    customer_services.delete_customer(db, customer_id)
    return {"message": "Customer deleted successfully"}

@router.get("/{customer_id}/summary", response_model=CustomerSummaryOut)
def customer_summary(customer_id: int, db: Session = Depends(get_db)):
    return loan_services.get_customer_summary(db, customer_id)