from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict,field_validator,EmailStr
from typing import Literal

class CustomerIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr  #make it lowercase
    phone: str
    date_of_birth: date
    monthly_income: Decimal

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be empty")
        if len(value)<3:
            raise ValueError("Name must be at least 3 characters long")
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
        if value >= date.today():
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



class LoanApplyIn(BaseModel):
    customer_id: int = Field(gt=0)
    amount: Decimal = Field(ge=10_000, le=5_000_000, decimal_places=2)
    tenure_months: Literal[12, 24, 36, 48, 60]


class LoanOut(BaseModel):
    id: int
    customer_id: int
    amount: Decimal
    tenure_months: int
    interest_rate: Decimal | None
    emi: Decimal | None
    status: str
    rejection_reason: str | None
    applied_on: date

    model_config = {"from_attributes": True}