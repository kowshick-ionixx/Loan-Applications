from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, computed_field

Username = Annotated[
    str,
    Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.@]+$"),
    AfterValidator(str.lower),
]


class RegisterRequest(BaseModel):
    username: Username
    password: str = Field(min_length=8, max_length=128)


class RegisterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str
    customer_id: int | None

    @computed_field
    @property
    def has_customer_profile(self) -> bool:
        return self.customer_id is not None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
