from sqlalchemy.orm import Session

from loan_application.db import transaction
from loan_application.exceptions import AppError, ForbiddenError, ProfileExistsError
from loan_application.models import Customer, User, UserRole
from loan_application.repositories import customer_repository
from loan_application.schemas.customer import CustomerCreate

DUPLICATE_EMAIL = ("DUPLICATE_EMAIL", "Email already exists")


def create_customer(db: Session, data: CustomerCreate, user: User) -> Customer:
    is_customer = user.role == UserRole.CUSTOMER
    if is_customer and user.customer_id is not None:
        raise ProfileExistsError()
    customer = Customer(**data.model_dump())
    with transaction(db, *DUPLICATE_EMAIL):
        customer_repository.add(db, customer)
        if is_customer:
            user.customer_id = customer.id
    return customer


def check_owner(user: User, customer_id: int | None) -> None:
    if user.role == UserRole.CUSTOMER and user.customer_id != customer_id:
        raise ForbiddenError()


def get_customer(db: Session, customer_id: int) -> Customer:
    customer = customer_repository.get_by_id(db, customer_id)
    if customer is None:
        raise AppError(404, "NOT_FOUND", f"Customer with id {customer_id} not found")
    return customer


def get_customer_for_user(db: Session, customer_id: int, user: User) -> Customer:
    # Ownership first, so a customer cannot tell which other ids exist.
    check_owner(user, customer_id)
    return get_customer(db, customer_id)
