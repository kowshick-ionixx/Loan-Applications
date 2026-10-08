from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from loan_application.db import MAX_ID

LoanStatus = Literal["APPROVED", "REJECTED"]


class LoanCreate(BaseModel):
    customer_id: int = Field(gt=0, le=MAX_ID, strict=True)
    amount: Decimal = Field(ge=10000, le=5000000, decimal_places=2)
    tenure_months: Literal[12, 24, 36, 48, 60]


class LoanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    amount: float
    tenure_months: int
    interest_rate: float | None
    emi: float | None
    status: LoanStatus
    rejection_reason: str | None
    applied_on: date
