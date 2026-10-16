import os
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url

from loan_application.config import settings

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or make_url(
    settings.database_url
).set(database="app_db_test").render_as_string(hide_password=False)
if not (make_url(TEST_DATABASE_URL).database or "").endswith("_test"):
    pytest.exit("Refusing to run: the test database name must end with _test", 1)
settings.database_url = TEST_DATABASE_URL

from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from alembic import command
from loan_application.db import engine, get_db
from loan_application.main import app
from loan_application.models import Customer, User
from loan_application.schemas.customer import CustomerCreate
from loan_application.security import hash_password

PASSWORD = "Password@123"
PROFILE = {
    "name": "Meena Das",
    "email": "meena@example.com",
    "phone": "9876543210",
    "date_of_birth": "1990-05-15",
    "monthly_income": 50000,
}


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    assert (engine.url.database or "").endswith("_test")
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    command.upgrade(Config(Path(__file__).parents[1] / "alembic.ini"), "head")


@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create(client, officer, **fields):
    response = client.post(
        "/api/customers", headers=officer, json={**PROFILE, **fields}
    )
    assert response.status_code == 201, response.json()
    return response.json()["id"]


def fields_of(response):
    return {d["field"] for d in response.json()["details"]}


def error_of(response):
    return response.json()["error"]


def login(client, username, password=PASSWORD):
    form = {"username": username, "password": password}
    response = client.post("/auth/login", data=form)
    assert response.status_code == 200, response.json()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def register(client, username, password=PASSWORD, **extra):
    """Register a CUSTOMER login; it has no profile until POST /api/customers."""
    body = {**extra, "username": username, "password": password}
    return client.post("/auth/register", json=body)


def apply(client, headers, customer_id, amount=100000, tenure_months=12):
    body = {
        "customer_id": customer_id,
        "amount": amount,
        "tenure_months": tenure_months,
    }
    return client.post("/api/loans", headers=headers, json=body)


@pytest.fixture
def officer(client, db):
    db.add(
        User(username="officer1", password_hash=hash_password(PASSWORD), role="OFFICER")
    )
    db.commit()
    return login(client, "officer1")


@pytest.fixture
def signup(client, db):
    """A customer profile with a linked CUSTOMER login, the way
    scripts/seed.py create_customer_user() makes one; then log in."""

    def _signup(email="meena@example.com", **profile):
        username = email.split("@")[0]
        data = CustomerCreate.model_validate({**PROFILE, "email": email, **profile})
        customer = Customer(**data.model_dump())
        db.add(customer)
        db.flush()
        db.add(
            User(
                username=username,
                password_hash=hash_password(PASSWORD),
                role="CUSTOMER",
                customer_id=customer.id,
            )
        )
        db.commit()
        return login(client, username), customer.id

    return _signup


@pytest.fixture
def profileless(client, db):
    """A CUSTOMER login without a profile (e.g. after their profile was deleted)."""
    db.add(
        User(
            username="noprofile", password_hash=hash_password(PASSWORD), role="CUSTOMER"
        )
    )
    db.commit()
    return login(client, "noprofile")


def pytest_report_teststatus(report):
    if report.when == "call" and report.passed:
        return "passed", ".", ("PASS", {"green": True})
    if report.failed:
        return "failed", "F", ("FAIL", {"red": True})
    return None
