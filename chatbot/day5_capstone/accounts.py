from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# The database URL lives in the project root .env, as for the Day 2 login.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from loan_application.db import SessionLocal
from loan_application.models import UserRole
from loan_application.services.auth_service import authenticate_user

CUSTOMER = UserRole.CUSTOMER
MANAGER = UserRole.OFFICER
BAD_LOGIN = "Invalid username, password or role."


@dataclass(frozen=True)
class UserContext:
    """Who is logged in. Passed to the agent on every call, so each session
    is checked against its own user."""

    username: str
    role: str
    customer_id: int | None = None

    @property
    def is_manager(self) -> bool:
        return self.role == MANAGER


def customer_number(customer_id) -> int | None:
    """'C161', ' 161 ' or 161 -> 161. Anything that is not an ID -> None."""
    key = str(customer_id).strip().upper().removeprefix("C")
    return int(key) if key.isdigit() else None


def can_see_customer(user: UserContext, customer_id) -> bool:
    """Managers see every customer; a customer sees only their own record."""
    if user.is_manager:
        return True
    return customer_number(customer_id) == user.customer_id


def login(username: str, password: str, role: str) -> tuple[UserContext | None, str]:
    """Check a login against the users table. Returns (user, "") or (None, why)."""
    if not username.strip() or not password:
        return None, "Please enter a username and a password."
    with SessionLocal() as db:
        user = authenticate_user(db, username, password)
        if user is None or user.role != role:
            return None, BAD_LOGIN
        if user.role == CUSTOMER and user.customer_id is None:
            return None, "This login has no customer profile yet. Ask a manager."
        return UserContext(user.username, user.role, user.customer_id), ""
