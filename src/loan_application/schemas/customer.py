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
    field_validator,
)

RiskBand = Literal["LOW", "MEDIUM", "HIGH"]

Name = Annotated[
    str, Field(min_length=3, max_length=50, pattern=r"^[A-Za-z][A-Za-z ]*$")
]
Email = Annotated[EmailStr, AfterValidator(str.lower)]
Phone = Annotated[str, Field(pattern=r"^[0-9]{10}$")]
Income = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]
Address = Annotated[str, Field(min_length=1, max_length=255)]

# Fields a customer may change on their own profile; the rest need an officer.
CUSTOMER_EDITABLE = {"name", "phone", "address"}


class CustomerCreate(BaseModel):
    name: Name
    email: Email
    phone: Phone
    date_of_birth: PastDate
    monthly_income: Income
    address: Address | None = None


class CustomerUpdate(BaseModel):
    """PATCH body: only the fields sent are changed. Unknown fields are ignored."""

    name: Name | None = None
    email: Email | None = None
    phone: Phone | None = None
    date_of_birth: PastDate | None = None
    monthly_income: Income | None = None
    address: Address | None = None

    # Runs only for fields that were sent; address may be cleared with null.
    @field_validator("name", "email", "phone", "date_of_birth", "monthly_income")
    @classmethod
    def not_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("cannot be null")
        return value

    def changes(self) -> dict:
        return self.model_dump(exclude_unset=True)


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    phone: str
    date_of_birth: date
    monthly_income: float
    address: str | None


class CustomerPage(BaseModel):
    items: list[CustomerOut]
    page: int
    size: int
    total: int
    pages: int


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
