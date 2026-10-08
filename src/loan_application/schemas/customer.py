from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, PastDate


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
