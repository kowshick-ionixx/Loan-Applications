from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, PastDate


class CustomerCreate(BaseModel):
    name: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z ]+$")
    email: EmailStr
    phone: str = Field(pattern=r"^[0-9]{10}$")
    date_of_birth: PastDate
    monthly_income: Decimal = Field(gt=0)


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    phone: str
    date_of_birth: date
    monthly_income: float
