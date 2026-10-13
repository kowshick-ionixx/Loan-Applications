import pytest
from conftest import PASSWORD

from loan_application.db import SessionLocal
from loan_application.models import User
from loan_application.scripts.seed import create_customer_user, create_or_reset_officer
from loan_application.security import verify_password

# The seed script commits through its own session, so clean up by hand.
USERNAME = "seed_test_officer"


@pytest.fixture
def cleanup():
    yield
    with SessionLocal() as db:
        db.query(User).filter(User.username.in_([USERNAME, "seed_customer"])).delete()
        db.commit()


def stored_user(username):
    with SessionLocal() as db:
        return db.query(User).filter_by(username=username).one_or_none()


def existing_user(username):
    user = stored_user(username)
    assert user is not None
    return user


def test_officer_is_created_then_reset(cleanup, capsys):
    create_or_reset_officer(USERNAME, PASSWORD)
    assert existing_user(USERNAME).role == "OFFICER"

    create_or_reset_officer(USERNAME, "New@Password1")
    assert verify_password("New@Password1", existing_user(USERNAME).password_hash)
    assert "password reset" in capsys.readouterr().out


def test_customer_user_needs_existing_customer(cleanup, capsys):
    create_customer_user("seed_customer", PASSWORD, customer_id=999999)
    assert "not found" in capsys.readouterr().out
    assert stored_user("seed_customer") is None

    create_customer_user("seed_customer", PASSWORD)
    assert existing_user("seed_customer").customer_id is None
