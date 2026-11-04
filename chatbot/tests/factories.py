"""Synthetic customers for the isolated test database.

Every value is derived from the thresholds loaded at test time, never typed
in. Customer IDs are the table's integer auto IDs (get_customer only accepts
digits); the TEST-<uuid8> tag goes into the email so every row is unique.
existing_emi is not a column: it is the sum of the customer's APPROVED loans,
so a customer with an existing EMI gets one APPROVED loan row.
"""

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

import oracle
from sqlalchemy import func, select

from loan_application.db import SessionLocal
from loan_application.models import Customer, Loan


def dob_for_age(age: int) -> date:
    """A date of birth that makes the customer exactly `age` today."""
    today = datetime.now().astimezone().date()  # the same "today" get_customer uses
    birthday = today - timedelta(days=60)  # birthday already passed this year
    if birthday.month == 2 and birthday.day == 29:
        birthday = birthday.replace(day=28)
    return birthday.replace(year=birthday.year - age)


@dataclass
class Seeded:
    id: int
    tag: str
    age: int
    monthly_income: float
    credit_score: int
    existing_emi: float

    @property
    def record(self) -> dict:
        """The fields the oracle needs."""
        return {
            "age": self.age,
            "monthly_income": self.monthly_income,
            "credit_score": self.credit_score,
            "existing_emi": self.existing_emi,
        }


class CustomerFactory:
    def __init__(self, thresholds: dict):
        self.t = thresholds

    # ---------- the base builder ----------

    def make_customer(
        self,
        *,
        age: int | None = None,
        monthly_income: float | None = None,
        credit_score: int | None = None,
        existing_emi: float = 0.0,
        name: str = "Test Customer",
    ) -> Seeded:
        t = self.t
        age = (t["min_age"] + t["max_age"]) // 2 if age is None else age
        income = t["min_income"] * 4 if monthly_income is None else monthly_income
        credit = (
            min(900, t["min_credit"] + 30) if credit_score is None else credit_score
        )
        tag = f"TEST-{uuid.uuid4().hex[:8]}"
        with SessionLocal() as db:
            customer = Customer(
                name=name,
                email=f"{tag.lower()}@example.com",
                phone=f"9{int(tag[5:], 16) % 10**9:09d}",
                date_of_birth=dob_for_age(age),
                monthly_income=Decimal(f"{income:.2f}"),
                credit_score=credit,
            )
            db.add(customer)
            db.flush()
            if existing_emi > 0:
                db.add(
                    Loan(
                        customer_id=customer.id,
                        amount=Decimal(100000),
                        tenure_months=36,
                        interest_rate=Decimal(str(t["rate"])),
                        emi=Decimal(f"{existing_emi:.2f}"),
                        status="APPROVED",
                    )
                )
            db.commit()
            return Seeded(customer.id, tag, age, income, credit, round(existing_emi, 2))

    # ---------- scenarios ----------

    def eligible(self) -> Seeded:
        return self.make_customer()

    def low_credit_refer(self) -> Seeded:
        t = self.t
        return self.make_customer(credit_score=(t["refer_from"] + t["min_credit"]) // 2)

    def very_low_credit(self) -> Seeded:
        return self.make_customer(credit_score=max(300, self.t["reject_below"] - 20))

    def underage(self) -> Seeded:
        return self.make_customer(age=self.t["min_age"] - 1)

    def overage(self) -> Seeded:
        return self.make_customer(age=self.t["max_age"] + 1)

    def low_income(self) -> Seeded:
        return self.make_customer(monthly_income=self.t["min_income"] - 1000)

    def burden_limit(self, amount: float, tenure: int, income: float) -> float:
        """The largest existing EMI that keeps the burden at the limit."""
        new_emi = oracle.emi_paise(amount, self.t["rate"], tenure)
        return self.t["burden_pct"] / 100 * income - new_emi

    def burden_fail(self, amount: float, tenure: int, **overrides) -> Seeded:
        income = overrides.pop("monthly_income", self.t["min_income"] * 4)
        existing = max(1000.0, self.burden_limit(amount, tenure, income) + 1000)
        return self.make_customer(
            monthly_income=income, existing_emi=existing, **overrides
        )

    def burden_at_limit(self, amount: float, tenure: int) -> Seeded:
        """Existing EMI chosen so existing + new EMI is exactly the limit."""
        income = self.t["min_income"] * 4
        existing = round(self.burden_limit(amount, tenure, income), 2)
        assert existing > 0, "amount too large for an exact-limit case"
        return self.make_customer(monthly_income=income, existing_emi=existing)

    def multi_fail(self, amount: float, tenure: int) -> Seeded:
        """Credit below reject_below (so both the Day 2 and Day 4 credit rules
        fail) and the burden rule fails too."""
        return self.burden_fail(
            amount, tenure, credit_score=max(300, self.t["reject_below"] - 10)
        )


def set_credit_score(customer_id: int, credit_score: int) -> None:
    with SessionLocal() as db:
        db.get(Customer, customer_id).credit_score = credit_score
        db.commit()


def unknown_customer_id() -> int:
    with SessionLocal() as db:
        return (db.scalar(select(func.max(Customer.id))) or 0) + 1000


def customer_count() -> int:
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(Customer))
