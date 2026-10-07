from datetime import date
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, func,CheckConstraint,Integer,Date
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name:Mapped[str]= mapped_column(String(50),nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True , nullable=False)
    phone: Mapped[str] = mapped_column(String(10), nullable=False)
    date_of_birth: Mapped[date]=mapped_column(Date, nullable=False)
    monthly_income: Mapped[Decimal] = mapped_column(Numeric(12, 2),nullable=False)

    __table_args__ =(
        CheckConstraint("char_length(phone) = 10", name="check_customer_phone_length"),
        CheckConstraint("char_length(name)>=3 AND char_length(name)<=50", name="check_customer_name_length"),
        CheckConstraint("name ~ '^[A-Za-z ]+$'", name="check_customer_name_letters"),
        CheckConstraint("date_of_birth < current_date",name="check_customer_date_of_birth"),
        CheckConstraint("monthly_income >0",name="check_monthly_income"),


    )



class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tenure_months: Mapped[int]=mapped_column(Integer,nullable=False)
    interest_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2),nullable=True)
    emi: Mapped[Decimal | None] = mapped_column(Numeric(12, 2),nullable=True)
    status: Mapped[str] = mapped_column(String(10))
    rejection_reason: Mapped[str | None] = mapped_column(String(255))
    applied_on: Mapped[date] = mapped_column(server_default=func.current_date())

    __table_args__=(
        CheckConstraint("amount>=10000 AND amount<=5000000",name="check_amount"),
        CheckConstraint("tenure_months IN (12,24,36,48,60)",name="check_loan_tenure"),
        CheckConstraint("status IN ('APPROVED', 'REJECTED')", name="check_loan_status"),
        CheckConstraint("status = 'REJECTED' OR rejection_reason IS NULL",name="check_rejection_reason"),   

                        

    )