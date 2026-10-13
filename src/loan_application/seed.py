from sqlalchemy.exc import IntegrityError

from loan_application.db import SessionLocal
from loan_application.repositories import user_repositories
from loan_application.security import hash_password
from loan_application.tables import Customer, User, UserRole

USERNAME = "officer1"
PASSWORD = "Officer@123"


def main() -> None:
    with SessionLocal() as db:
        if user_repositories.get_by_username(db, USERNAME):
            print("Officer already exists")
            return
        db.add(
            User(
                username=USERNAME,
                password_hash=hash_password(PASSWORD),
                role=UserRole.OFFICER,
            )
        )
        try:
            db.commit()
        except IntegrityError as e:
            db.rollback()
            print(f"Could not create officer: {e.orig}")
            return
        print("Officer created")


def create_customer_user(username: str, password: str, customer_id: int) -> None:
    with SessionLocal() as db:
        if user_repositories.get_by_username(db, username):
            print("User already exists")
            return

        if db.get(Customer, customer_id) is None:
            print(
                f"Customer with id {customer_id} not found in loan_db - create it first "
                f"with POST /customers/ as officer1, then use the id it returns"
            )
            return

        db.add(
            User(
                username=username,
                password_hash=hash_password(password),
                role=UserRole.CUSTOMER,
                customer_id=customer_id,
            )
        )
        try:
            db.commit()
        except IntegrityError as e:
            db.rollback()
            print(f"Could not create user: {e.orig}")
            return
        print(f"Customer user '{username}' created for customer {customer_id}")


if __name__ == "__main__":
    main()
