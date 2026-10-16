from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    PastDate,
)

from loan_application.schemas.auth import Username

RiskBand = Literal["LOW", "MEDIUM", "HIGH"]

Name = Annotated[
    str, Field(min_length=3, max_length=50, pattern=r"^[A-Za-z][A-Za-z ]*$")
]
Email = Annotated[EmailStr, AfterValidator(str.lower)]
Phone = Annotated[str, Field(pattern=r"^[0-9]{10}$")]
Income = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]
Address = Annotated[str, Field(min_length=1, max_length=255)]


class CustomerCreate(BaseModel):
    name: Name
    email: Email
    phone: Phone
    date_of_birth: PastDate
    monthly_income: Income
    address: Address | None = None
    username: Username | None = Field(default=None, exclude=True)


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    phone: str
    date_of_birth: date
    monthly_income: float
    address: str | None


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
