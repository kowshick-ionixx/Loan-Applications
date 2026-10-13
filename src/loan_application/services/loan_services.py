from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from loan_application.exceptions import (
    CustomerNotFound,
    InvalidInputError,
    NotFoundError,
)
from loan_application.repositories import customer_repositories, loan_repositories
from loan_application.schemas.loan_schemas import LoanApplyIn
from loan_application.tables import Customer, Loan
VALID_STATUSES = {"APPROVED", "REJECTED"}
from loan_application.services import customer_services

INTEREST_RATES = {
    12: Decimal(10),
    24: Decimal(11),
    36: Decimal(12),
    48: Decimal(13),
    60: Decimal(13),
}


def calculate_age(dob: date, today: date) -> int:
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

    if loan_repositories.count_approved_for_customer(db, customer.id) >= 2:
        return "Customer already has 2 active loans"

    return None


def apply_for_loan(db: Session, data: LoanApplyIn) -> Loan:
    customer = customer_repositories.get_by_id(db, data.customer_id)
    if customer is None:
        raise CustomerNotFound(data.customer_id)

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

    loan_repositories.add(db, loan)
    db.commit()
    db.refresh(loan)
    return loan


def get_loan(db: Session, loan_id: int) -> Loan:
    if loan_id <= 0: 
        raise InvalidInputError("id must be a positive integer")
    loan = loan_repositories.get_by_id(db, loan_id)
    if loan is None:
        raise NotFoundError(f"Loan {loan_id} not found")
    return loan


def risk_band(ratio: Decimal) -> str:
    if ratio < 30:
        return "LOW"
    if ratio <= 50:
        return "MEDIUM"
    return "HIGH"


def get_customer_summary(db: Session, customer_id: int) -> dict:
    customer = customer_repositories.get_by_id(db, customer_id)
    if customer is None:
        raise CustomerNotFound(customer_id)

    total, approved, rejected, approved_amount, approved_emi = (
        loan_repositories.summary_for_customer(db, customer_id)
    )
    approved_amount = Decimal(approved_amount)
    approved_emi = Decimal(approved_emi)

    if customer.monthly_income > 0:
        ratio = (approved_emi / customer.monthly_income * 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    else:
        ratio = Decimal("0.00")

    return {
        "customer_id": customer.id,
        "customer_name": customer.name,
        "total_applications": total,
        "approved_count": approved,
        "rejected_count": rejected,
        "total_approved_amount": approved_amount,
        "total_monthly_emi": approved_emi,
        "emi_to_income_ratio": ratio,
        "risk_band": risk_band(ratio),
    }


def approve_loan(db: Session, loan_id: int) -> Loan:
    loan = loan_repositories.get_by_id(db, loan_id)

    if loan is None:
        raise NotFoundError("Loan not found")

    if loan.status == "APPROVED":
        return loan

    rate = INTEREST_RATES[loan.tenure_months]
    loan.interest_rate = rate
    loan.emi = calculate_emi(
        loan.amount,
        rate,
        loan.tenure_months,
    )
    loan.status = "APPROVED"
    loan.rejection_reason = None

    db.commit()
    db.refresh(loan)
    return loan


def patch_loan(db: Session, loan_id: int) -> Loan:
    loan = loan_repositories.get_by_id(db, loan_id)

    if loan is None:
        raise NotFoundError("Loan not found")

    loan.status = "REJECTED"
    loan.interest_rate = None
    loan.emi = None
    loan.rejection_reason = "Rejected by administrator"

    db.commit()
    db.refresh(loan)
    return loan


def delete_loan(db: Session, loan_id: int) -> None:
    loan = loan_repositories.get_by_id(db, loan_id)

    if loan is None:
        raise NotFoundError("Loan not found")

    db.delete(loan)
    db.commit()


def list_loans_for_customer(
    db: Session,
    customer_id: int,
    status: str | None = None,
) -> list[Loan]:
    customer = customer_repositories.get_by_id(db, customer_id)

    if customer is None:
        raise CustomerNotFound(customer_id)

    if status is not None:
        status = status.upper()
        if status not in {"APPROVED", "REJECTED"}:
            raise InvalidInputError("Status must be APPROVED or REJECTED")

    return loan_repositories.list_for_customer(
        db,
        customer_id,
        status,
    )






def list_customer_loans(db: Session, customer_id: int, status: str | None = None):
    if status is not None and status not in VALID_STATUSES:
        raise InvalidInputError("status must be APPROVED or REJECTED")

    customer_services.get_customer(db, customer_id)  # raises 400 or 404
    return loan_repositories.list_by_customer(db, customer_id, status)
