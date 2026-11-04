import os
import sys
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from dotenv import dotenv_values
from sqlalchemy.engine import make_url

DAY5 = Path(__file__).resolve().parent.parent
ROOT = DAY5.parents[1]
sys.path.insert(0, str(DAY5))

# Never touch the dev database: point the app at app_db_test before any import.
_dev = os.environ.get("DATABASE_URL") or dotenv_values(ROOT / ".env")["DATABASE_URL"]
_test = make_url(
    os.environ.get("TEST_DATABASE_URL") or make_url(_dev).set(database="app_db_test")
)
if not (_test.database or "").endswith("_test"):
    pytest.exit("Refusing to run: the test database name must end with _test", 1)
os.environ["DATABASE_URL"] = _test.render_as_string(hide_password=False)

from accounts import CUSTOMER, MANAGER, UserContext
from approval_graph import sqlite_graph
from cases import thread_config
from enquiry_reader import LoanEnquiry

from loan_application.db import SessionLocal, engine
from loan_application.models import Customer, User
from loan_application.services.auth_service import add_user

# Synthetic stand-ins for the two customers these tests were written against:
# 161 is approved for 5 lakh / 36 months; 162 (credit 701, income 45,000) is
# referred for 2 lakh / 24 months and rejected on burden for 10 lakh / 36 months.
SAMPLE_CUSTOMERS = [
    {"id": 161, "name": "vetri", "credit_score": 725, "monthly_income": 80000},
    {"id": 162, "name": "agilan", "credit_score": 701, "monthly_income": 45000},
]


@pytest.fixture(scope="session", autouse=True)
def test_database():
    """Fresh schema from the app's migrations, plus the two sample customers."""
    from alembic.config import Config
    from sqlalchemy import text

    from alembic import command

    assert (engine.url.database or "").endswith("_test")
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
    with SessionLocal() as db:
        for sample in SAMPLE_CUSTOMERS:
            db.add(
                Customer(
                    **sample,
                    email=f"{sample['name']}@example.com",
                    phone="9000000000",
                    date_of_birth=date(1992, 1, 1),
                )
            )
        db.commit()
        db.execute(text("SELECT setval('customers_id_seq', 1000)"))
        db.commit()
    yield


@pytest.fixture
def graph(tmp_path):
    """The approval graph on a temporary SQLite file, one per test."""
    graph = sqlite_graph(tmp_path / "checkpoints.db")
    yield graph
    graph.checkpointer.conn.close()


@pytest.fixture
def prefilled():
    """Run a case with a hand-filled enquiry instead of the model: the state
    is written as if intake had just run, then the graph continues from validate.
    Fast and deterministic; validate still looks the customer up in Postgres."""

    def run(graph, thread_id: str, customer_id: str, amount, tenure_months):
        missing = [
            name
            for name, value in (("amount", amount), ("tenure_months", tenure_months))
            if value is None
        ]
        enquiry = LoanEnquiry(
            amount=amount,
            tenure_months=tenure_months,
            confidence="high" if not missing else "medium",
            missing_fields=missing,
        )
        config = thread_config(thread_id)
        graph.update_state(
            config,
            {
                "customer_id": customer_id,
                "email": "(pre-filled for the test)",
                "enquiry": enquiry,
                "log": ["intake: pre-filled"],
            },
            as_node="intake",
        )
        graph.invoke(None, config)
        return graph.get_state(config)

    return run


MANAGER_USER = UserContext("test-manager", MANAGER)


@pytest.fixture(scope="session")
def accounts_in_db():
    """A temporary customer with a customer login, and a manager login.
    Deleted again after the test session."""
    tag = uuid.uuid4().hex[:8]
    password = f"Pw-{tag}-day5"
    with SessionLocal() as db:
        customer = Customer(
            name="Day Five Tester",
            email=f"day5-{tag}@example.com",
            phone="9000000000",
            date_of_birth=date(1990, 1, 1),
            monthly_income=Decimal(60000),
            credit_score=730,
        )
        db.add(customer)
        db.commit()
        customer_id = customer.id
        customer_user = add_user(
            db, f"day5-cust-{tag}", password, CUSTOMER, customer_id
        )
        manager_user = add_user(db, f"day5-mgr-{tag}", password, MANAGER)
        logins = {
            "password": password,
            "customer": customer_user.username,
            "manager": manager_user.username,
            "customer_id": customer_id,
        }
    yield logins
    with SessionLocal() as db:
        for username in (logins["customer"], logins["manager"]):
            user = db.query(User).filter_by(username=username).one_or_none()
            if user is not None:
                db.delete(user)
        db.commit()
        customer = db.get(Customer, customer_id)
        if customer is not None:
            db.delete(customer)
        db.commit()
