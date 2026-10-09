from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from loan_application.db import DATABASE_URL, Base
from loan_application.models import Customer

TEST_DB_NAME = "test_app_db"
TODAY = date(2026, 10, 8)


@pytest.fixture
def today() -> date:
    return TODAY


@pytest.fixture
def make_customer():
    def _make(age: int = 30, income: str = "50000") -> Customer:
        dob = date(TODAY.year - age, TODAY.month, TODAY.day)
        return Customer(
            name="Test User",
            email="test@example.com",
            phone="9876543210",
            date_of_birth=dob,
            monthly_income=Decimal(income),
        )

    return _make


@pytest.fixture(scope="session")
def test_engine():
    main_url = make_url(DATABASE_URL)
    admin_url = main_url.set(database="postgres")
    test_url = main_url.set(database=TEST_DB_NAME)

    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME} WITH (FORCE)"))
        conn.execute(text(f"CREATE DATABASE {TEST_DB_NAME}"))

    engine = create_engine(test_url)
    Base.metadata.create_all(engine)
    yield engine

    engine.dispose()
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME} WITH (FORCE)"))
    admin.dispose()


@pytest.fixture
def db(test_engine):
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()
