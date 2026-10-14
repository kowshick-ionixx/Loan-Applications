import logging
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from loan_application.db import transaction
from loan_application.exceptions import AppError
from loan_application.models import APPROVED, REJECTED, Customer, Loan, User, UserRole
from loan_application.repositories import loan_repository
from loan_application.schemas.customer import CustomerSummary, RiskBand
from loan_application.schemas.loan import LoanCreate
from loan_application.services.customer_service import (
    check_owner,
    get_customer_for_user,
)

logger = logging.getLogger(__name__)

MIN_AGE = 21
MAX_AGE = 60
MAX_INCOME_MULTIPLE = 20
MAX_ACTIVE_LOANS = 2
LOW_RISK_BELOW = 30
HIGH_RISK_ABOVE = 50
CENTS = Decimal("0.01")

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
    return emi.quantize(CENTS, rounding=ROUND_HALF_UP)


def check_eligibility(
    customer: Customer, amount: Decimal, approved_count: int, today: date
) -> str | None:
    if not MIN_AGE <= calculate_age(customer.date_of_birth, today) <= MAX_AGE:
        return "Age must be between 21 and 60"
    if amount > MAX_INCOME_MULTIPLE * customer.monthly_income:
        return "Requested amount exceeds 20x monthly income"
    if approved_count >= MAX_ACTIVE_LOANS:
        return "Customer already has 2 active loans"
    return None


def get_risk_band(emi_to_income_ratio: Decimal) -> RiskBand:
    if emi_to_income_ratio < LOW_RISK_BELOW:
        return "LOW"
    if emi_to_income_ratio <= HIGH_RISK_ABOVE:
        return "MEDIUM"
    return "HIGH"


def apply_for_loan(db: Session, data: LoanCreate, user: User) -> Loan:
    customer = get_customer_for_user(db, data.customer_id, user)
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
        status=REJECTED if reason else APPROVED,
        rejection_reason=reason,
        applied_on=today,
    )
    # The customer could be deleted between the lookup and the insert.
    with transaction(db, "CUSTOMER_REMOVED", f"Customer {customer.id} was removed"):
        loan_repository.add(db, loan)
    logger.info("Loan %s %s for customer %s", loan.id, loan.status, customer.id)
    return loan


def get_loan(db: Session, loan_id: int, user: User) -> Loan:
    loan = loan_repository.get_by_id(db, loan_id)
    check_owner(user, loan.customer_id if loan else None)
    if loan is None:
        raise AppError(404, "NOT_FOUND", f"Loan with id {loan_id} not found")
    return loan


def list_loans(db: Session, status: str | None, user: User) -> list[Loan]:
    if user.role == UserRole.CUSTOMER:
        return loan_repository.list_for_customer(db, user.customer_id, status)
    return loan_repository.list_all(db, status)


def delete_loan(db: Session, loan_id: int, user: User) -> None:
    loan = get_loan(db, loan_id, user)
    loan_repository.delete(db, loan)
    db.commit()
    logger.info("Loan %s deleted", loan_id)


def list_customer_loans(
    db: Session, customer_id: int, status: str | None, user: User
) -> list[Loan]:
    get_customer_for_user(db, customer_id, user)
    return loan_repository.list_for_customer(db, customer_id, status)


def get_customer_summary(db: Session, customer_id: int, user: User) -> CustomerSummary:
    customer = get_customer_for_user(db, customer_id, user)
    loans = loan_repository.list_for_customer(db, customer_id, None)
    approved_loans = [loan for loan in loans if loan.status == APPROVED]

    total_emi = sum((loan.emi or Decimal(0) for loan in approved_loans), Decimal(0))
    ratio = (total_emi / customer.monthly_income * 100).quantize(
        CENTS, rounding=ROUND_HALF_UP
    )

    return CustomerSummary(
        customer_id=customer.id,
        customer_name=customer.name,
        total_applications=len(loans),
        approved_count=len(approved_loans),
        rejected_count=len(loans) - len(approved_loans),
        total_approved_amount=float(sum(loan.amount for loan in approved_loans)),
        total_monthly_emi=float(total_emi),
        emi_to_income_ratio=float(ratio),
        risk_band=get_risk_band(ratio),
    )
