import re
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class CustomerIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    email: EmailStr
    phone: str
    date_of_birth: date
    monthly_income: Decimal

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be empty")
        if len(value) < 3:
            raise ValueError("Name must be at least 3 characters long")
        if not re.fullmatch(r"[A-Za-z ]+", value):
            raise ValueError("Name must contain only letters and spaces")
        return value

    @field_validator("phone")
    @classmethod
    def phone_must_be_10digits(cls, value: str) -> str:
        if not value.isdigit() or len(value) != 10:
            raise ValueError("Phone number must be 10 digits")
        return value

    @field_validator("date_of_birth")
    @classmethod
    def dob_must_be_in_past(cls, value: date) -> date:
        if value >= datetime.now().astimezone().date():
            raise ValueError("Date of birth must be in the past")
        return value

    @field_validator("monthly_income")
    @classmethod
    def income_must_be_positive(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("Monthly income must be positive")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class CustomerOut(CustomerIn):
    id: int
    model_config = ConfigDict(from_attributes=True)


class CustomerSummaryOut(BaseModel):
    customer_id: int
    customer_name: str
    total_applications: int
    approved_count: int
    rejected_count: int
    total_approved_amount: float
    total_monthly_emi: float
    emi_to_income_ratio: float
    risk_band: Literal["LOW", "MEDIUM", "HIGH"]


class MessageOut(BaseModel):
    message: str
