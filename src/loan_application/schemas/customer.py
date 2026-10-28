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
CreditScore = Annotated[int, Field(ge=300, le=900)]


class CustomerCreate(BaseModel):
    name: Name
    email: Email
    phone: Phone
    date_of_birth: PastDate
    monthly_income: Income
    address: Address | None = None
    credit_score: CreditScore | None = None
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
    credit_score: int | None


class CreditScoreCheck(BaseModel):
    """Only the credit-score rule: passing it does not mean a loan will be
    approved, since age, income and active loans are checked too."""

    customer_id: int
    customer_name: str
    credit_score: int | None
    minimum_required: int
    meets_requirement: bool
    points_short: int | None
    message: str


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
