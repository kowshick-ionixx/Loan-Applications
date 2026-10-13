import os
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url

from loan_application.config import settings

# Point the app at the test database BEFORE db.py creates its engine.
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
from loan_application.models import User
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
    # Each test runs inside a transaction that is rolled back afterwards.
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


def login(client, username, password=PASSWORD):
    form = {"username": username, "password": password}
    response = client.post("/auth/login", data=form)
    assert response.status_code == 200, response.json()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def register(client, username, password=PASSWORD):
    body = {"username": username, "password": password}
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
    db.flush()
    return login(client, "officer1")


@pytest.fixture
def signup(client):
    """Register, log in and create the profile, like a real customer would."""

    def _signup(email="meena@example.com", **profile):
        username = email.split("@")[0]
        assert register(client, username).status_code == 201
        headers = login(client, username)
        body = {**PROFILE, "email": email, **profile}
        response = client.post("/api/customers", headers=headers, json=body)
        assert response.status_code == 201, response.json()
        return headers, response.json()["id"]

    return _signup


def pytest_report_teststatus(report):
    # One plain word per test: PASS in green, FAIL in red.
    if report.when == "call" and report.passed:
        return "passed", ".", ("PASS", {"green": True})
    if report.failed:
        return "failed", "F", ("FAIL", {"red": True})
    return None
