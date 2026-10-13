from loan_application.db import SessionLocal
from loan_application.repositories import user_repositories
from loan_application.security import hash_password
from loan_application.tables import User, UserRole
USERNAME = "officer"
PASSWORD = "ChangeMe123!"


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
        db.commit()
        print("Officer created")

def create_customer_user(username: str, password: str, customer_id: int) -> None:
    with SessionLocal() as db:
        if user_repositories.get_by_username(db, username):
            print("User already exists")
            return
        db.add(
            User(
                username=username,
                password_hash=hash_password(password),
                role=UserRole.CUSTOMER,
                customer_id=customer_id,
            )
        )
        db.commit()
        print("Customer user created")

if __name__ == "__main__":
    main()