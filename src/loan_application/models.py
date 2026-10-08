from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from loan_application.db import Base


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint(
            "char_length(name) BETWEEN 3 AND 50", name="ck_customers_name_length"
        ),
        CheckConstraint("name ~ '^[A-Za-z ]+$'", name="ck_customers_name_letters"),
        CheckConstraint("phone ~ '^[0-9]{10}$'", name="ck_customers_phone_10_digits"),
        CheckConstraint("monthly_income > 0", name="ck_customers_income_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(10))
    date_of_birth: Mapped[date]
    monthly_income: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Loan(Base):
    __tablename__ = "loans"
    __table_args__ = (
        CheckConstraint(
            "amount BETWEEN 10000 AND 5000000", name="ck_loans_amount_range"
        ),
        CheckConstraint(
            "tenure_months IN (12, 24, 36, 48, 60)", name="ck_loans_tenure_allowed"
        ),
        CheckConstraint(
            "status IN ('APPROVED', 'REJECTED')", name="ck_loans_status_allowed"
        ),
        CheckConstraint(
            "interest_rate IS NULL OR interest_rate > 0", name="ck_loans_rate_positive"
        ),
        CheckConstraint("emi IS NULL OR emi >= 0", name="ck_loans_emi_non_negative"),
        CheckConstraint(
            "(status = 'APPROVED' AND rejection_reason IS NULL AND emi IS NOT NULL AND interest_rate IS NOT NULL)"
            " OR (status = 'REJECTED' AND rejection_reason IS NOT NULL)",
            name="ck_loans_status_consistency",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tenure_months: Mapped[int]
    interest_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    emi: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(10))
    rejection_reason: Mapped[str | None] = mapped_column(String(255))
    applied_on: Mapped[date] = mapped_column(server_default=func.current_date())
