from sqlalchemy.orm import Session

from loan_application.db import transaction
from loan_application.exceptions import AppError, ForbiddenError, NotFoundError
from loan_application.models import Customer, User, UserRole
from loan_application.repositories import customer_repository, user_repository
from loan_application.schemas.customer import CustomerCreate

DUPLICATE_EMAIL = ("DUPLICATE_EMAIL", "Email already exists")


def check_email_free(db: Session, email: str) -> None:
    if customer_repository.get_by_email(db, email):
        raise AppError(409, *DUPLICATE_EMAIL)


def login_to_link(db: Session, data: CustomerCreate, user: User) -> User | None:
    """The login the new profile belongs to: the caller's own for a customer,
    the named CUSTOMER login for an officer, or none (an unlinked profile)."""
    if user.role == UserRole.CUSTOMER:
        owner = user
    elif data.username is None:
        return None
    else:
        owner = user_repository.get_by_username(db, data.username, lock=True)
        if owner is None:
            raise AppError(404, "NOT_FOUND", f"User '{data.username}' not found")
        if owner.role != UserRole.CUSTOMER:
            raise AppError(
                400, "NOT_A_CUSTOMER", f"User '{data.username}' is not a CUSTOMER login"
            )
    if owner.customer_id is not None:
        message = (
            "You already have a customer profile"
            if owner is user
            else f"User '{owner.username}' already has a customer profile"
        )
        raise AppError(409, "PROFILE_EXISTS", message)
    return owner


def create_customer(db: Session, data: CustomerCreate, user: User) -> Customer:
    """A customer creates their own profile, once, linked to their login. An
    officer creates one for the CUSTOMER login named in `username`, or an
    unlinked profile when no username is given."""
    with transaction(db, *DUPLICATE_EMAIL):
        owner = login_to_link(db, data, user)
        check_email_free(db, data.email)
        customer = Customer(**data.model_dump())
        customer_repository.add(db, customer)
        if owner is not None:
            owner.customer_id = customer.id
            db.flush()
    return customer


def check_owner(user: User, customer_id: int | None) -> None:
    if user.role == UserRole.CUSTOMER and user.customer_id != customer_id:
        raise ForbiddenError()


def get_customer(db: Session, customer_id: int, lock: bool = False) -> Customer:
    customer = customer_repository.get_by_id(db, customer_id, lock)
    if customer is None:
        raise NotFoundError("Customer", customer_id)
    return customer


def get_customer_for_user(
    db: Session, customer_id: int, user: User, lock: bool = False
) -> Customer:
    check_owner(user, customer_id)
    return get_customer(db, customer_id, lock)
