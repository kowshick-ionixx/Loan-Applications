from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, PastDate

RiskBand = Literal["LOW", "MEDIUM", "HIGH"]


class CustomerCreate(BaseModel):
    name: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z][A-Za-z ]*$")
    email: Annotated[EmailStr, AfterValidator(str.lower)]
    phone: str = Field(pattern=r"^[0-9]{10}$")
    date_of_birth: PastDate
    monthly_income: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    phone: str
    date_of_birth: date
    monthly_income: float


class CustomerSummary(BaseModel):
    customer_id: int
    customer_name: str
    total_applications: int
    approved_count: int
    rejected_count: int
    total_approved_amount: float
    total_monthly_emi: float
    emi_to_income_ratio: float
    risk_band: RiskBand
