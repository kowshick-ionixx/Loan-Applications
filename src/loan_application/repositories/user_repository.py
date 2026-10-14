from sqlalchemy import select
from sqlalchemy.orm import Session

from loan_application.models import User


def add(db: Session, user: User) -> None:
    db.add(user)
    db.flush()


def get_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username))


def list_all(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)))
