from sqlalchemy.orm import Session

from loan_application.exceptions import AppError, ForbiddenError, NotFoundError
from loan_application.models import User, UserRole
from loan_application.repositories import user_repository
from loan_application.security import hash_password, verify_password


def get_user(db: Session, user_id: int) -> User:
    user = user_repository.get_by_id(db, user_id)
    if user is None:
        raise NotFoundError("User", user_id)
    return user


def get_user_for(db: Session, user_id: int, current: User) -> User:
    # A customer may only see themselves, whether or not the other id exists.
    if current.role == UserRole.CUSTOMER and current.id != user_id:
        raise ForbiddenError()
    return get_user(db, user_id)


def list_users(db: Session) -> list[User]:
    return user_repository.list_all(db)


def change_role(db: Session, user_id: int, role: str, current: User) -> User:
    if user_id == current.id and role != UserRole.OFFICER:
        raise AppError(403, "CANNOT_DEMOTE_SELF", "Officers cannot demote themselves")
    user = get_user(db, user_id)
    user.role = role
    if role == UserRole.OFFICER:
        # Officers have no customer profile; the profile and its loans stay.
        user.customer_id = None
    db.commit()
    return user


def change_password(db: Session, user: User, old: str, new: str) -> None:
    if not verify_password(old, user.password_hash):
        raise AppError(400, "WRONG_PASSWORD", "Old password is incorrect")
    user.password_hash = hash_password(new)
    db.commit()


def deactivate_user(db: Session, user_id: int, current: User) -> None:
    if user_id == current.id:
        raise AppError(
            403, "CANNOT_DEACTIVATE_SELF", "Officers cannot deactivate themselves"
        )
    user = get_user(db, user_id)
    user.is_active = False
    db.commit()
