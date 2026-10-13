from sqlalchemy.orm import Session

from loan_application.repositories import user_repositories
from loan_application.security import verify_password
from loan_application.tables import User


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = user_repositories.get_by_username(db, username)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user