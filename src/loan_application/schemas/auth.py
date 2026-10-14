from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

Username = Annotated[
    str,
    Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.@]+$"),
    AfterValidator(str.lower),
]
Password = Annotated[str, Field(min_length=8, max_length=128)]


class RegisterRequest(BaseModel):
    """Only the login; the customer profile is created with POST /api/customers."""

    username: Username
    password: Password


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
