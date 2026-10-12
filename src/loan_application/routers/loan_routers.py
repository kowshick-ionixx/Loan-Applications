from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from loan_application.db import get_db
from loan_application.schemas.loan_schemas import LoanApplyIn, LoanOut, messageOut
from loan_application.services import loan_services

router = APIRouter(prefix="/loans", tags=["Loans"])


@router.post("/apply", response_model=LoanOut, status_code=201)
def apply_loan(data: LoanApplyIn, db: Session = Depends(get_db)):
    return loan_services.apply_for_loan(db, data)


@router.get("/{loan_id}", response_model=LoanOut)
def get_loan(loan_id: int, db: Session = Depends(get_db)):
    return loan_services.get_loan(db, loan_id)


@router.get("/", response_model=list[LoanOut])
def list_loans(
    customer_id: int, status: str | None = None, db: Session = Depends(get_db)
):
    return loan_services.list_loans_for_customer(db, customer_id, status)


# @router.put("/{loan_id}/approve", response_model=LoanOut)

# def approve_loan(loan_id: int, db: Session = Depends(get_db)):
#     return loan_services.approve_loan(db, loan_id)

# @router.patch("/{loan_id}/reject", response_model=LoanOut)
# def patch_loan(loan_id: int, db: Session = Depends(get_db)):
#     return loan_services.patch_loan(db, loan_id)


@router.delete("/{loan_id}", response_model=messageOut, status_code=200)
def delete_loan(loan_id: int, db: Session = Depends(get_db)):
    loan_services.delete_loan(db, loan_id)
    return {"message": f"Loan {loan_id} deleted successfully"}
