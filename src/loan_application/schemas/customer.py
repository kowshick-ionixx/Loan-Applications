from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, PastDate


# Data the client sends (POST /api/customers). Pydantic checks every field.
class CustomerCreate(BaseModel):
    name: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z ]+$")
    email: EmailStr
    phone: str = Field(pattern=r"^[0-9]{10}$")
    date_of_birth: PastDate
    monthly_income: Decimal = Field(gt=0)


# Data the API sends back.
class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # read values from a Customer object

    id: int
    name: str
    email: str
    phone: str
    date_of_birth: date
    monthly_income: float
