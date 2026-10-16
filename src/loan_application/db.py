from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from loan_application.config import settings
from loan_application.exceptions import AppError

DATABASE_URL = settings.database_url
MAX_ID = 2**31 - 1

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


type DbSession = Annotated[Session, Depends(get_db)]


@contextmanager
def transaction(
    db: Session, error: str | None = None, message: str = ""
) -> Iterator[None]:
    """The service layer's unit of work: wrap every read and write of one
    operation, so it commits once at the end or not at all.

    Any exception rolls everything back. A unique/foreign-key clash becomes a
    409 with the given error code (or is re-raised when none is given)."""
    try:
        yield
        db.commit()
    except IntegrityError:
        db.rollback()
        if error is None:
            raise
        raise AppError(409, error, message) from None
    except BaseException:
        db.rollback()
        raise
