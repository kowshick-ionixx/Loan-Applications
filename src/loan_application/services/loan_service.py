import logging
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from loan_application.exceptions import AppError
from loan_application.models import Customer, Loan
from loan_application.repositories import loan_repository
from loan_application.schemas.customer import CustomerSummary
from loan_application.schemas.loan import LoanCreate
from loan_application.services.customer_service import get_customer

logger = logging.getLogger(__name__)

INTEREST_RATES = {
    12: Decimal(10),
    24: Decimal(11),
    36: Decimal(12),
    48: Decimal(13),
    60: Decimal(13),
}


def calculate_age(dob: date, today: date) -> int:
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def calculate_emi(amount: Decimal, annual_rate: Decimal, months: int) -> Decimal:
    r = annual_rate / 12 / 100
    factor = (1 + r) ** months
    emi = amount * r * factor / (factor - 1)
    return emi.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def check_eligibility(
    customer: Customer, amount: Decimal, approved_count: int, today: date
) -> str | None:
    if not 21 <= calculate_age(customer.date_of_birth, today) <= 60:
        return "Age must be between 21 and 60"
    if amount > 20 * customer.monthly_income:
        return "Requested amount exceeds 20x monthly income"
    if approved_count >= 2:
        return "Customer already has 2 active loans"
    return None


def apply_for_loan(db: Session, data: LoanCreate) -> Loan:
    customer = get_customer(db, data.customer_id)
    today = datetime.now().astimezone().date()
    approved_count = loan_repository.count_approved_for_customer(db, customer.id)
    reason = check_eligibility(customer, data.amount, approved_count, today)
    rate = INTEREST_RATES[data.tenure_months]

    loan = Loan(
        customer_id=customer.id,
        amount=data.amount,
        tenure_months=data.tenure_months,
        interest_rate=rate,
        emi=None if reason else calculate_emi(data.amount, rate, data.tenure_months),
        status="REJECTED" if reason else "APPROVED",
        rejection_reason=reason,
        applied_on=today,
    )
    loan_repository.add(db, loan)
    db.commit()
    logger.info("Loan %s %s for customer %s", loan.id, loan.status, customer.id)
    return loan


def get_loan(db: Session, loan_id: int) -> Loan:
    loan = loan_repository.get_by_id(db, loan_id)
    if loan is None:
        raise AppError(404, "NOT_FOUND", f"Loan with id {loan_id} not found")
    return loan


def list_customer_loans(
    db: Session, customer_id: int, status: str | None
) -> list[Loan]:
    get_customer(db, customer_id)
    return loan_repository.list_for_customer(db, customer_id, status)


def get_customer_summary(db: Session, customer_id: int) -> CustomerSummary:
    customer = get_customer(db, customer_id)
    loans = loan_repository.list_for_customer(db, customer_id, None)
    approved_loans = [loan for loan in loans if loan.status == "APPROVED"]

    return CustomerSummary(
        customer_id=customer.id,
        name=customer.name,
        total_loans=len(loans),
        approved_loans=len(approved_loans),
        rejected_loans=len(loans) - len(approved_loans),
        total_approved_amount=sum(loan.amount for loan in approved_loans),
        total_monthly_emi=sum(loan.emi or 0 for loan in approved_loans),
    )
