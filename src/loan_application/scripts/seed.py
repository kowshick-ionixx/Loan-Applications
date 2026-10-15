import getpass

from sqlalchemy.exc import IntegrityError

from loan_application.config import settings
from loan_application.db import SessionLocal
from loan_application.exceptions import AppError
from loan_application.models import Customer, UserRole
from loan_application.repositories import user_repository
from loan_application.security import hash_password
from loan_application.services.auth_service import add_user


def create_customer_user(
    username: str, password: str, customer_id: int | None = None
) -> None:
    with SessionLocal() as db:
        if customer_id is not None and db.get(Customer, customer_id) is None:
            print(f"Customer with id {customer_id} not found - create it first")
            return
        try:
            user = add_user(
                db, username.lower(), password, UserRole.CUSTOMER, customer_id
            )
        except AppError as e:
            print(f"Could not create user: {e.message}")
            return
        print(f"CUSTOMER user '{user.username}' created (id={user.id})")


def link_customer_user(username: str, customer_id: int) -> None:
    """Link an existing CUSTOMER login (e.g. from POST /auth/register) to a
    profile an officer created, so the login can reach that profile."""
    with SessionLocal() as db:
        user = user_repository.get_by_username(db, username.lower())
        if user is None or user.role != UserRole.CUSTOMER:
            print(f"CUSTOMER user '{username}' not found")
            return
        if user.customer_id is not None:
            print(f"User '{user.username}' is already linked to {user.customer_id}")
            return
        if db.get(Customer, customer_id) is None:
            print(f"Customer with id {customer_id} not found - create it first")
            return
        user.customer_id = customer_id
        try:
            db.commit()
        except IntegrityError:
            print(f"Customer {customer_id} is already linked to another login")
            return
        print(f"User '{user.username}' linked to customer {customer_id}")


def create_or_reset_officer(username: str, password: str) -> None:
    with SessionLocal() as db:
        user = user_repository.get_by_username(db, username)
        if user is None:
            user = add_user(db, username, password, UserRole.OFFICER)
            print(f"OFFICER '{username}' created (id={user.id})")
            return
        if user.role != UserRole.OFFICER:
            print(f"User '{username}' exists but is not an OFFICER")
            return
        user.password_hash = hash_password(password)
        user.is_active = True
        db.commit()
        print(f"OFFICER '{username}' password reset (id={user.id})")


def main() -> None:
    username = settings.seed_officer_username.lower()
    password = settings.seed_officer_password or getpass.getpass(
        f"Password for {username}: "
    )
    create_or_reset_officer(username, password)


def create_officer_user(username: str, password: str) -> None:
    with SessionLocal() as db:
        try:
            user = add_user(db, username.lower(), password, UserRole.OFFICER)
        except AppError as e:
            print(f"Could not create user: {e.message}")
            return
        print(f"OFFICER user '{user.username}' created (id={user.id})")


if __name__ == "__main__":
    main()
