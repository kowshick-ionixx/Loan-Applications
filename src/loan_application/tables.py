from datetime import date
from decimal import Decimal
import enum
from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, Numeric, String, func,Enum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, validates




class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    monthly_income: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    @validates("date_of_birth")
    def validate_date_of_birth(self, key, value):
        if value >= date.today():
            raise ValueError("Date of birth must be in the past")
        return value

    __table_args__ = (
        CheckConstraint("length(phone) = 10", name="check_customer_phone_length"),
        CheckConstraint(
            "length(name)>=3 AND length(name)<=50", name="check_customer_name_length"
        ),
        CheckConstraint(
            "name NOT GLOB '*[^A-Za-z ]*'", name="check_customer_name_letters"
        ),
        CheckConstraint("monthly_income >0", name="check_monthly_income"),
    )


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tenure_months: Mapped[int] = mapped_column(Integer, nullable=False)
    interest_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    emi: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(10))
    rejection_reason: Mapped[str | None] = mapped_column(String(255))
    applied_on: Mapped[date] = mapped_column(server_default=func.current_date())

    __table_args__ = (
        CheckConstraint("amount>=10000 AND amount<=5000000", name="check_amount"),
        CheckConstraint("tenure_months IN (12,24,36,48,60)", name="check_loan_tenure"),
        CheckConstraint("status IN ('APPROVED', 'REJECTED')", name="check_loan_status"),
        CheckConstraint(
            "status = 'REJECTED' OR rejection_reason IS NULL",
            name="check_rejection_reason",
        ),
    )


class UserRole(str, enum.Enum):
    OFFICER = "OFFICER"
    CUSTOMER = "CUSTOMER"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"))
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id"), unique=True, nullable=True
    )
    is_active: Mapped[bool] = mapped_column(default=True)