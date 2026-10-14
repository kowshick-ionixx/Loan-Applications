import math

from sqlalchemy.orm import Session

from loan_application.db import transaction
from loan_application.exceptions import AppError, ForbiddenError, NotFoundError
from loan_application.models import Customer, User, UserRole
from loan_application.repositories import customer_repository, loan_repository
from loan_application.schemas.customer import (
    CUSTOMER_EDITABLE,
    CustomerCreate,
    CustomerOut,
    CustomerPage,
    CustomerUpdate,
)

DUPLICATE_EMAIL = ("DUPLICATE_EMAIL", "Email already exists")


def check_email_free(db: Session, email: str) -> None:
    if customer_repository.get_by_email(db, email):
        raise AppError(409, *DUPLICATE_EMAIL)


def create_customer(db: Session, data: CustomerCreate, user: User) -> Customer:
    """An officer creates an unlinked profile; a customer creates their own,
    once, and it is linked to their login."""
    is_customer = user.role == UserRole.CUSTOMER
    if is_customer and user.customer_id is not None:
        raise AppError(409, "PROFILE_EXISTS", "You already have a customer profile")
    check_email_free(db, data.email)
    customer = Customer(**data.model_dump())
    # The unique index still catches two requests racing for the same email.
    with transaction(db, *DUPLICATE_EMAIL):
        customer_repository.add(db, customer)
        if is_customer:
            user.customer_id = customer.id
            db.flush()
    return customer


def list_customers(db: Session, page: int, size: int) -> CustomerPage:
    total = customer_repository.count(db)
    customers = customer_repository.list_page(db, (page - 1) * size, size)
    return CustomerPage(
        items=[CustomerOut.model_validate(c) for c in customers],
        page=page,
        size=size,
        total=total,
        pages=math.ceil(total / size),
    )


def check_owner(user: User, customer_id: int | None) -> None:
    if user.role == UserRole.CUSTOMER and user.customer_id != customer_id:
        raise ForbiddenError()


def get_customer(db: Session, customer_id: int) -> Customer:
    customer = customer_repository.get_by_id(db, customer_id)
    if customer is None:
        raise NotFoundError("Customer", customer_id)
    return customer


def get_customer_for_user(db: Session, customer_id: int, user: User) -> Customer:
    # Ownership first, so a customer cannot tell which other ids exist.
    check_owner(user, customer_id)
    return get_customer(db, customer_id)


def get_own_customer(db: Session, user: User) -> Customer:
    customer = customer_repository.get_by_id(db, user.customer_id or 0)
    if customer is None:
        raise AppError(404, "NOT_FOUND", "You do not have a customer profile")
    return customer


def update_customer(
    db: Session, customer_id: int, data: CustomerUpdate, user: User
) -> Customer:
    check_owner(user, customer_id)
    changes = data.changes()
    if user.role == UserRole.CUSTOMER:
        locked = sorted(set(changes) - CUSTOMER_EDITABLE)
        if locked:
            raise ForbiddenError(
                f"Customers can only change name, phone and address, not {', '.join(locked)}"
            )
    customer = get_customer(db, customer_id)
    if "email" in changes and changes["email"] != customer.email:
        check_email_free(db, changes["email"])
    with transaction(db, *DUPLICATE_EMAIL):
        for field, value in changes.items():
            setattr(customer, field, value)
        db.flush()
    return customer


def message_has_active_loans(customer_id: int) -> str:
    return f"Customer {customer_id} has active loans and cannot be deleted"


def delete_customer(db: Session, customer_id: int) -> None:
    """Allowed only without APPROVED loans; their rejected applications go too."""
    customer = get_customer(db, customer_id)
    if loan_repository.count_approved_for_customer(db, customer_id):
        raise AppError(
            409, "CUSTOMER_HAS_ACTIVE_LOANS", message_has_active_loans(customer_id)
        )
    # An approved loan added meanwhile still trips the foreign key -> 409.
    error = ("CUSTOMER_HAS_ACTIVE_LOANS", message_has_active_loans(customer_id))
    with transaction(db, *error):
        loan_repository.delete_inactive_for_customer(db, customer_id)
        customer_repository.delete(db, customer)
