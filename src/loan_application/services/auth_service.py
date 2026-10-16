from sqlalchemy.orm import Session

from loan_application.db import transaction
from loan_application.exceptions import DuplicateUsernameError
from loan_application.models import User, UserRole
from loan_application.repositories import user_repository
from loan_application.schemas.auth import RegisterRequest
from loan_application.security import hash_password, verify_password

DUMMY_HASH = hash_password("dummy-password")


def add_user(
    db: Session,
    username: str,
    password: str,
    role: str,
    customer_id: int | None = None,
) -> User:
    with transaction(db, "DUPLICATE_USERNAME", f"Username '{username}' already exists"):
        if user_repository.get_by_username(db, username):
            raise DuplicateUsernameError(username)
        user = User(
            username=username,
            password_hash=hash_password(password),
            role=role,
            customer_id=customer_id,
        )
        user_repository.add(db, user)
    db.refresh(user)
    return user


def register(db: Session, data: RegisterRequest) -> User:
    """Create a CUSTOMER login with no profile yet."""
    return add_user(db, data.username, data.password, UserRole.CUSTOMER)


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    username = username.strip().lower()
    user = user_repository.get_by_username(db, username)
    password_ok = verify_password(password, user.password_hash if user else DUMMY_HASH)
    if user is None or not password_ok or not user.is_active:
        return None
    return user
