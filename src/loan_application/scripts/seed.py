import getpass

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


if __name__ == "__main__":
    main()
