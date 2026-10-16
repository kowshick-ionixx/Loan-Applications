"""Auth, tokens, errors on every endpoint, logging and seeding."""

import json
import logging
import sys
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from conftest import (
    PASSWORD,
    PROFILE,
    error_of,
    login,
    register,
)

from loan_application.config import settings
from loan_application.db import SessionLocal
from loan_application.logging_config import JsonFormatter, LogContextFilter
from loan_application.models import Customer, User
from loan_application.schemas.customer import CustomerCreate
from loan_application.scripts.seed import (
    create_customer_user,
    create_or_reset_officer,
    link_customer_user,
)
from loan_application.security import verify_password


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_request_id_header_and_error_body(client):
    response = client.get("/api/loans/1", headers={"X-Request-ID": "abc123"})
    assert response.headers["X-Request-ID"] == "abc123"
    assert response.json()["request_id"] == "abc123"


def test_register_creates_login_without_profile(client, db):
    response = register(client, "Meena.Das")
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "meena.das"
    assert body["role"] == "CUSTOMER" and body["is_active"] is True
    assert body["customer_id"] is None and body["has_customer_profile"] is False
    assert PASSWORD not in response.text and "password" not in body
    assert db.get(User, body["id"]).password_hash != PASSWORD


def test_register_ignores_profile_fields(client, db):
    response = register(client, "meena", **PROFILE)
    assert response.status_code == 201
    assert response.json()["customer_id"] is None


def test_register_duplicate_username(client):
    register(client, "meena")
    response = register(client, "MEENA")
    assert response.status_code == 409
    assert error_of(response) == "DUPLICATE_USERNAME"


def test_register_lists_every_invalid_field(client):
    body = {"username": "a!", "password": "short"}
    response = client.post("/auth/register", json=body)
    assert response.status_code == 400
    assert error_of(response) == "VALIDATION_FAILED"
    fields = {d["field"] for d in response.json()["details"]}
    assert fields == {"username", "password"}


def test_register_ignores_role_in_body(client):
    response = register(client, "sneaky", role="OFFICER")
    assert response.status_code == 201
    assert response.json()["role"] == "CUSTOMER"


def test_login_success_is_case_insensitive(client, signup):
    signup()
    login(client, "MEENA")


@pytest.mark.parametrize(
    ("username", "password"), [("meena", "wrong-password"), ("nobody", PASSWORD)]
)
def test_login_wrong_username_or_password(client, signup, username, password):
    signup()
    response = client.post(
        "/auth/login", data={"username": username, "password": password}
    )
    assert response.status_code == 401
    assert error_of(response) == "INVALID_CREDENTIALS"


def test_login_inactive_user(client, db, signup):
    signup()
    db.query(User).filter_by(username="meena").one().is_active = False
    db.flush()
    response = client.post(
        "/auth/login", data={"username": "meena", "password": PASSWORD}
    )
    assert response.status_code == 401


def token_for(user_id, minutes):
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "role": "OFFICER", "iat": now}
    payload["exp"] = now + timedelta(minutes=minutes)
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


@pytest.mark.parametrize(
    "token", [None, "not-a-jwt", token_for(1, -5)], ids=["none", "invalid", "expired"]
)
def test_bad_token_is_401(client, token):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    response = client.get("/api/loans/1", headers=headers)
    assert response.status_code == 401
    assert error_of(response) == "UNAUTHORIZED"
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json()["request_id"]


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/customers/1"),
        ("get", "/api/customers/1/summary"),
        ("get", "/api/customers/1/loans"),
        ("post", "/api/loans"),
        ("get", "/api/loans/1"),
    ],
)
def test_customer_without_profile_gets_403(client, profileless, method, path):
    headers = profileless
    body = {**PROFILE, "customer_id": 1, "amount": 100000, "tenure_months": 12}
    response = client.request(method, path, headers=headers, json=body)
    assert response.status_code == 403
    assert error_of(response) == "CUSTOMER_PROFILE_REQUIRED"


def test_user_id_is_in_log_context(client, db, officer, caplog):
    caplog.handler.addFilter(LogContextFilter())
    officer_id = db.query(User).filter_by(username="officer1").one().id
    client.get("/api/customers/999999", headers=officer)
    logged = [
        r for r in caplog.records if "GET /api/customers/999999" in r.getMessage()
    ]
    assert logged and logged[-1].user_id == officer_id
    client.get("/health")
    anonymous = [r for r in caplog.records if "GET /health" in r.getMessage()]
    assert anonymous and anonymous[-1].user_id == "-"


def test_docker_health_probe_is_not_logged(client, caplog):
    caplog.set_level(logging.INFO)
    client.get("/health", headers={"X-Health-Probe": "docker"})
    assert not [r for r in caplog.records if "GET /health" in r.getMessage()]
    client.get("/health")
    assert [r for r in caplog.records if "GET /health" in r.getMessage()]


LOAN = {"customer_id": 1, "amount": 100000, "tenure_months": 12}


PROTECTED = [
    ("post", "/api/customers"),
    ("get", "/api/customers/{id}"),
    ("get", "/api/customers/{id}/summary"),
    ("get", "/api/customers/{id}/loans"),
    ("post", "/api/loans"),
    ("get", "/api/loans"),
    ("get", "/api/loans/{id}"),
]


WITH_ID = [(method, path) for method, path in PROTECTED if "{id}" in path]


WITH_BODY = [("post", "/api/customers"), ("post", "/api/loans")]


def body_for(path):
    if path.startswith("/api/loans"):
        return LOAN
    return PROFILE


@pytest.mark.parametrize(("method", "path"), PROTECTED)
def test_no_token_is_401(client, method, path):
    url = path.format(id=1)
    response = client.request(method, url, json=body_for(path))
    assert response.status_code == 401
    assert error_of(response) == "UNAUTHORIZED"
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize(("method", "path"), WITH_BODY)
@pytest.mark.parametrize("token", [None, "not-a-jwt"], ids=["no-token", "bad-token"])
def test_malformed_json_without_valid_token_is_401(client, method, path, token):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = path.format(id=1)
    response = client.request(method, url, headers=headers, content='{"name": ')
    assert response.status_code == 401
    assert error_of(response) == "UNAUTHORIZED"


@pytest.mark.parametrize(("method", "path"), WITH_BODY)
def test_malformed_json_with_valid_token_is_400(client, officer, method, path):
    headers = {**officer, "Content-Type": "application/json"}
    url = path.format(id=1)
    response = client.request(method, url, headers=headers, content='{"name": ')
    assert response.status_code == 400
    assert error_of(response) == "INVALID_REQUEST"


def test_malformed_json_on_public_endpoint_is_400(client):
    headers = {"Content-Type": "application/json"}
    response = client.post("/auth/register", headers=headers, content='{"a": ')
    assert response.status_code == 400
    assert error_of(response) == "INVALID_REQUEST"


@pytest.mark.parametrize(("method", "path"), WITH_ID)
@pytest.mark.parametrize("bad_id", ["abc", "0", "-1"])
def test_bad_id_is_400(client, officer, method, path, bad_id):
    url = path.format(id=bad_id)
    response = client.request(method, url, headers=officer, json=body_for(path))
    assert response.status_code == 400
    assert error_of(response) == "VALIDATION_FAILED"


@pytest.mark.parametrize(("method", "path"), WITH_ID)
def test_missing_record_is_404_for_officer(client, officer, method, path):
    url = path.format(id=999999)
    response = client.request(method, url, headers=officer, json=body_for(path))
    assert response.status_code == 404
    assert error_of(response) == "NOT_FOUND"


def test_token_of_deactivated_user_is_401(client, db, signup):
    headers, customer_id = signup()
    db.query(User).filter_by(username="meena").one().is_active = False
    db.flush()
    response = client.get(f"/api/customers/{customer_id}", headers=headers)
    assert response.status_code == 401
    assert error_of(response) == "UNAUTHORIZED"


def test_token_of_deleted_user_is_401(client, db, signup):
    headers, customer_id = signup()
    db.delete(db.query(User).filter_by(username="meena").one())
    db.flush()
    response = client.get(f"/api/customers/{customer_id}", headers=headers)
    assert response.status_code == 401


@pytest.mark.parametrize("missing", ["username", "password"])
def test_login_missing_field_is_400(client, missing):
    form = {"username": "meena", "password": "Password@123"}
    del form[missing]
    response = client.post("/auth/login", data=form)
    assert response.status_code == 400
    assert response.json()["details"][0]["field"] == missing


def log_record(msg, exc_info=None):
    record = logging.LogRecord("app", logging.ERROR, __file__, 1, msg, (), exc_info)
    LogContextFilter().filter(record)
    return record


def test_json_log_line_carries_context():
    line = json.loads(JsonFormatter().format(log_record("GET /health -> 200")))
    assert line["message"] == "GET /health -> 200"
    assert line["level"] == "ERROR"
    assert line["request_id"] == "-" and line["user_id"] == "-"
    assert "exception" not in line


def test_json_log_line_keeps_exception_server_side():
    try:
        raise RuntimeError("database exploded")
    except RuntimeError:
        record = log_record("Unhandled error", sys.exc_info())
    line = json.loads(JsonFormatter().format(record))
    assert "database exploded" in line["exception"]


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


@pytest.fixture
def unlinked_customer():
    with SessionLocal() as db:
        data = CustomerCreate.model_validate({**PROFILE, "email": "link@example.com"})
        customer = Customer(**data.model_dump())
        db.add(customer)
        db.commit()
        customer_id = customer.id
    yield customer_id
    with SessionLocal() as db:
        db.query(User).filter_by(username="seed_customer").delete()
        db.query(Customer).filter_by(id=customer_id).delete()
        db.commit()


def test_link_customer_user(unlinked_customer, client, capsys):
    link_customer_user("seed_customer", unlinked_customer)
    assert "not found" in capsys.readouterr().out

    create_customer_user("seed_customer", PASSWORD)
    link_customer_user("seed_customer", 999999)
    assert "not found" in capsys.readouterr().out

    link_customer_user("SEED_CUSTOMER", unlinked_customer)
    assert existing_user("seed_customer").customer_id == unlinked_customer
    headers = login(client, "seed_customer")
    response = client.get(f"/api/customers/{unlinked_customer}", headers=headers)
    assert response.status_code == 200

    link_customer_user("seed_customer", unlinked_customer)
    assert "already linked" in capsys.readouterr().out


def test_tampered_token_is_401(client, signup):
    headers, customer_id = signup()
    token = headers["Authorization"].removeprefix("Bearer ")
    header, payload, signature = token.split(".")
    flipped = signature[:-2] + ("AA" if signature[-2:] != "AA" else "BB")
    for bad in (f"{header}.{payload}.{flipped}", f"{header}.{payload}."):
        response = client.get(
            f"/api/customers/{customer_id}",
            headers={"Authorization": f"Bearer {bad}"},
        )
        assert response.status_code == 401


def test_register_login_then_create_own_profile(client, db):
    registered = register(client, "kavya")
    assert registered.status_code == 201
    token = login(client, "kavya")
    body = {**PROFILE, "email": "kavya@example.com", "address": "Chennai"}
    created = client.post("/api/customers", headers=token, json=body)
    assert created.status_code == 201
    customer_id = created.json()["id"]
    assert db.get(User, registered.json()["id"]).customer_id == customer_id
    response = client.get(f"/api/customers/{customer_id}", headers=token)
    assert response.status_code == 200
    assert response.json() == {**body, "id": customer_id}
