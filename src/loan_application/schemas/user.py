from typing import Literal

from pydantic import BaseModel, ConfigDict, computed_field

Role = Literal["OFFICER", "CUSTOMER"]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: Role
    customer_id: int | None
    is_active: bool

    @computed_field
    @property
    def has_customer_profile(self) -> bool:
        return self.customer_id is not None
