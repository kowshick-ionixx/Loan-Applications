from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from loan_application.exceptions import ConflictError, CustomerNotFound,InvalidInputError
from loan_application.repositories import customer_repositories
from loan_application.schemas.customer_schemas import CustomerIn
from loan_application.tables import Customer
from loan_application.exceptions import InvalidInputError, CustomerNotFound
from loan_application.repositories import customer_repositories  

DUPLICATE_EMAIL = "Customer with this email already exists"


def _commit(db: Session, message: str) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(message)



from loan_application.repositories import customer_repositories  


def get_customer(db, customer_id: int):
    if customer_id < 0:
        raise InvalidInputError("id must be a positive integer")
    customer = customer_repositories.get_by_id(db, customer_id)
    if customer is None:
        raise CustomerNotFound(customer_id)
    return customer


def create_customer(db: Session, data: CustomerIn) -> Customer:
    customer_data = data.model_dump()
    customer_data["email"] = data.email.strip().lower()

    if customer_repositories.email_exists(db, customer_data["email"]):
        raise ConflictError(DUPLICATE_EMAIL)

    customer = Customer(**customer_data)
    customer_repositories.add(db, customer)

    _commit(db, DUPLICATE_EMAIL)
    db.refresh(customer)

    return customer


def update_customer(db: Session, customer_id: int, data: CustomerIn) -> Customer:
    customer = get_customer(db, customer_id)

    if customer_repositories.email_taken_by_other(db, data.email, customer_id):
        raise ConflictError(DUPLICATE_EMAIL)

    for key, value in data.model_dump().items():
        setattr(customer, key, value)
    _commit(db, DUPLICATE_EMAIL)
    db.refresh(customer)
    return customer


def delete_customer(db: Session, customer_id: int) -> None:
    customer = get_customer(db, customer_id)
    customer_repositories.delete(db, customer)
    _commit(db, "Customer has loan records and cannot be deleted")
