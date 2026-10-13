from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from loan_application.db import get_db
from loan_application.schemas.customer_schemas import (
    CustomerIn,
    CustomerOut,
    CustomerSummaryOut,
    MessageOut,
)
from loan_application.dependencies.auth import get_current_user, require_roles,authenticated_user
from loan_application.services import customer_services, loan_services
from loan_application.services.access import ensure_can_access_customer
from loan_application.schemas.loan_schemas import LoanOut
from loan_application.tables import User, UserRole

router = APIRouter(prefix="/customers", tags=["Customers"],  dependencies=[Depends(authenticated_user)],)
officer_only = [Depends(require_roles(UserRole.OFFICER))]


@router.post("/", response_model=CustomerOut, status_code=201)
def add_customer(data: CustomerIn, db: Session = Depends(get_db)):
    return customer_services.create_customer(db, data)


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, db: Session = Depends(get_db),user: User = Depends(get_current_user),):
    ensure_can_access_customer(user, customer_id)
    return customer_services.get_customer(db, customer_id)


@router.put("/{customer_id}", response_model=CustomerOut)
def update_customer(
    customer_id: int,
    data: CustomerIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ensure_can_access_customer(user, customer_id)
    if user.role == UserRole.CUSTOMER:
        current = customer_services.get_customer(db, customer_id)
        if (
            data.monthly_income != current.monthly_income
            or data.date_of_birth != current.date_of_birth
        ):
            raise HTTPException(
                status_code=403,
                detail="Only an officer can change income or date of birth",
            )
    return customer_services.update_customer(db, customer_id, data)

@router.delete("/{customer_id}", response_model=MessageOut, status_code=200, dependencies=officer_only,)
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    customer_services.delete_customer(db, customer_id)
    return {"message": "Customer deleted successfully"}


@router.get("/{customer_id}/summary", response_model=CustomerSummaryOut)
def customer_summary(customer_id: int, db: Session = Depends(get_db),user: User = Depends(get_current_user),):
    ensure_can_access_customer(user, customer_id)
    return loan_services.get_customer_summary(db, customer_id)





@router.get("/{customer_id}/loans", response_model=list[LoanOut])
def customer_loans(
    customer_id: int, 
    status: str | None = None, 
    db: Session = Depends(get_db), 
    user: User = Depends(get_current_user),
    ):
    ensure_can_access_customer(user, customer_id)
    return loan_services.list_customer_loans(db, customer_id, status)