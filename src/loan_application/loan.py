from datetime import date
from decimal import Decimal, ROUND_HALF_UP


from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from loan_application.schemas import LoanApplyIn, LoanOut
from loan_application.db import get_db            
from loan_application.tables import Customer, Loan

router = APIRouter(prefix="/loans", tags=["Loans"])







# ---------- Business logic ----------

INTEREST_RATES = {
    12: Decimal("10"),
    24: Decimal("11"),
    36: Decimal("12"),
    48: Decimal("13"),
    60: Decimal("13"),
}


def calculate_age(dob: date, today: date) -> int:
    # subtract 1 if the birthday has not happened yet this year
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def calculate_emi(principal: Decimal, annual_rate: Decimal, months: int) -> Decimal:
    r = annual_rate / Decimal(12) / Decimal(100)
    factor = (1 + r) ** months
    emi = principal * r * factor / (factor - 1)
    return emi.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def check_eligibility(db: Session, customer: Customer, amount: Decimal) -> str | None:
    """Return the rejection reason of the first failed rule, or None if eligible."""
    age = calculate_age(customer.date_of_birth, date.today())
    if not (21 <= age <= 60):
        return "Age must be between 21 and 60"

    if amount > 20 * customer.monthly_income:
        return "Requested amount exceeds 20x monthly income"

    approved_count = db.scalar(
        select(func.count())
        .select_from(Loan)
        .where(Loan.customer_id == customer.id, Loan.status == "APPROVED")
    )
    if approved_count >= 2:
        return "Customer already has 2 active loans"

    return None


# ---------- Endpoint for loan application ---------

@router.post("/apply", response_model=LoanOut, status_code=201)
def apply_loan(data: LoanApplyIn, db: Session = Depends(get_db)):
    # Customer must exist
    customer = db.get(Customer, data.customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Eligibility rules (first failure wins)
    reason = check_eligibility(db, customer, data.amount)

    if reason:
        loan = Loan(
            customer_id=customer.id,
            amount=data.amount,
            tenure_months=data.tenure_months,
            status="REJECTED",
            rejection_reason=reason,
        )
    else:
        rate = INTEREST_RATES[data.tenure_months]
        loan = Loan(
            customer_id=customer.id,
            amount=data.amount,
            tenure_months=data.tenure_months,
            interest_rate=rate,
            emi=calculate_emi(data.amount, rate, data.tenure_months),
            status="APPROVED",
        )

  
    db.add(loan)
    db.commit()
    db.refresh(loan)   

    return loan