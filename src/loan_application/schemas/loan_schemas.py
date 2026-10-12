from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LoanApplyIn(BaseModel):
    customer_id: int = Field(gt=0)
    amount: Decimal = Field(
        ge=10_000,
        le=5_000_000,
        decimal_places=2,
    )
    tenure_months: Literal[12, 24, 36, 48, 60]


class LoanOut(BaseModel):
    id: int
    customer_id: int
    amount: Decimal
    tenure_months: int
    interest_rate: Decimal | None
    emi: Decimal | None
    status: Literal["APPROVED", "REJECTED"]
    rejection_reason: str | None
    applied_on: date

    model_config = ConfigDict(from_attributes=True)


class LoanSummaryOut(BaseModel):
    customer_id: int
    customer_name: str
    total_applications: int
    approved_count: int
    rejected_count: int
    total_approved_amount: Decimal
    total_monthly_emi: Decimal
    emi_to_income_ratio: Decimal
    risk_band: Literal["LOW", "MEDIUM", "HIGH"]


class messageOut(BaseModel):
    message: str
