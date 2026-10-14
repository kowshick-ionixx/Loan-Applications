"""Auth, users, tokens, errors on every endpoint, logging and seeding."""

import json
import logging
import sys
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from conftest import (
    EXTRA,
    PASSWORD,
    PROFILE,
    error_of,
    login,
    register,
)

from loan_application.config import settings
from loan_application.db import SessionLocal
from loan_application.logging_config import JsonFormatter, LogContextFilter
from loan_application.models import User
from loan_application.scripts.seed import create_customer_user, create_or_reset_officer
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


LOAN = {"customer_id": 1, "amount": 100000, "tenure_months": 12}


PROTECTED = [
    ("post", "/api/customers"),
    ("get", "/api/customers/{id}"),
    ("get", "/api/customers/{id}/summary"),
    ("get", "/api/customers/{id}/loans"),
    ("post", "/api/loans"),
    ("get", "/api/loans/{id}"),
]
# EXTRA APIs (commented out in the routers); add back to PROTECTED when enabled:
# ("get", "/api/customers"), ("get", "/api/customers/me"),
# ("patch", "/api/customers/{id}"), ("delete", "/api/customers/{id}"),
# ("get", "/api/loans"), ("delete", "/api/loans/{id}"),
# ("get", "/api/users"), ("get", "/api/users/me"), ("patch", "/api/users/me/password"),
# ("get", "/api/users/{id}"), ("patch", "/api/users/{id}/role"),
# ("delete", "/api/users/{id}")


WITH_ID = [(method, path) for method, path in PROTECTED if "{id}" in path]


WITH_BODY = [("post", "/api/customers"), ("post", "/api/loans")]
# EXTRA: ("patch", "/api/customers/{id}"), ("patch", "/api/users/{id}/role"),
# ("patch", "/api/users/me/password")


def body_for(path):
    if path.startswith("/api/loans"):
        return LOAN
    if path.endswith("/role"):
        return {"role": "OFFICER"}
    if path.endswith("/password"):
        return {"old_password": "Password@123", "new_password": "Password@456"}
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
    # Regression: FastAPI reads the body before checking the token, which used to
    # answer 400 INVALID_REQUEST to callers who were not logged in.
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


@EXTRA
@pytest.mark.parametrize(
    ("method", "path", "error"),
    [
        ("patch", "/api/customers/1", "CUSTOMER_PROFILE_REQUIRED"),
        ("get", "/api/loans", "CUSTOMER_PROFILE_REQUIRED"),
        ("delete", "/api/customers/1", "FORBIDDEN"),
        ("delete", "/api/loans/1", "FORBIDDEN"),
    ],
)
def test_customer_without_profile_is_403(client, profileless, method, path, error):
    response = client.request(method, path, headers=profileless, json=PROFILE)
    assert response.status_code == 403
    assert error_of(response) == error


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


def user_id(db, username):
    return db.query(User).filter_by(username=username).one().id


@EXTRA
def test_users_me(client, db, signup, officer):
    headers, customer_id = signup()
    me = client.get("/api/users/me", headers=headers).json()
    assert me["username"] == "meena" and me["role"] == "CUSTOMER"
    assert me["customer_id"] == customer_id and "password_hash" not in me
    assert client.get("/api/users/me", headers=officer).json()["role"] == "OFFICER"


@EXTRA
def test_user_by_id(client, db, signup, officer):
    meena, _ = signup()
    signup(email="ravi@example.com")
    meena_id, ravi_id = user_id(db, "meena"), user_id(db, "ravi")
    assert client.get(f"/api/users/{meena_id}", headers=meena).status_code == 200
    for other in (ravi_id, 999999):  # no probing which ids exist
        response = client.get(f"/api/users/{other}", headers=meena)
        assert response.status_code == 403
    assert client.get(f"/api/users/{ravi_id}", headers=officer).status_code == 200
    response = client.get("/api/users/999999", headers=officer)
    assert response.status_code == 404
    assert response.json()["message"] == "User with id 999999 not found"


@EXTRA
def test_only_officers_list_users(client, signup, officer):
    headers, _ = signup()
    assert client.get("/api/users", headers=headers).status_code == 403
    users = client.get("/api/users", headers=officer).json()
    assert {u["username"] for u in users} == {"officer1", "meena"}


@EXTRA
def test_officer_changes_role(client, db, signup, officer):
    headers, customer_id = signup()
    url = f"/api/users/{user_id(db, 'meena')}/role"
    promoted = client.patch(url, headers=officer, json={"role": "OFFICER"})
    assert promoted.status_code == 200
    assert promoted.json()["role"] == "OFFICER"
    # Officers have no profile; the customer record itself stays.
    assert promoted.json()["customer_id"] is None
    assert client.get(f"/api/customers/{customer_id}", headers=officer).is_success
    # The role is read from the database, so the old token now acts as officer.
    assert client.get("/api/users", headers=headers).status_code == 200
    demoted = client.patch(url, headers=officer, json={"role": "CUSTOMER"})
    assert demoted.json()["role"] == "CUSTOMER"


@EXTRA
def test_officer_cannot_demote_themselves(client, db, officer):
    url = f"/api/users/{user_id(db, 'officer1')}/role"
    response = client.patch(url, headers=officer, json={"role": "CUSTOMER"})
    assert response.status_code == 403
    assert error_of(response) == "CANNOT_DEMOTE_SELF"
    assert client.get("/api/users/me", headers=officer).json()["role"] == "OFFICER"


@EXTRA
def test_role_change_rules(client, db, signup, officer):
    headers, _ = signup()
    url = f"/api/users/{user_id(db, 'meena')}/role"
    assert (
        client.patch(url, headers=headers, json={"role": "OFFICER"}).status_code == 403
    )
    bad = client.patch(url, headers=officer, json={"role": "ADMIN"})
    assert bad.status_code == 400 and bad.json()["details"][0]["field"] == "role"
    missing = client.patch(
        "/api/users/999999/role", headers=officer, json={"role": "OFFICER"}
    )
    assert missing.status_code == 404


@EXTRA
@pytest.mark.parametrize("who", ["officer", "customer"])
def test_change_own_password(client, signup, officer, who):
    if who == "customer":
        headers, _ = signup()
        username = "meena"
    else:
        headers, username = officer, "officer1"
    body = {"old_password": PASSWORD, "new_password": "NewSecret@1"}
    response = client.patch("/api/users/me/password", headers=headers, json=body)
    assert response.status_code == 200
    assert response.json() == {"message": "Password changed successfully"}
    form = {"username": username, "password": PASSWORD}
    assert client.post("/auth/login", data=form).status_code == 401
    login(client, username, "NewSecret@1")


@EXTRA
def test_change_password_needs_correct_old_password(client, signup):
    headers, _ = signup()
    body = {"old_password": "wrong-password", "new_password": "NewSecret@1"}
    response = client.patch("/api/users/me/password", headers=headers, json=body)
    assert response.status_code == 400
    assert error_of(response) == "WRONG_PASSWORD"
    login(client, "meena")  # unchanged


@EXTRA
def test_change_password_validates_new_password(client, signup):
    headers, _ = signup()
    body = {"old_password": PASSWORD, "new_password": "short"}
    response = client.patch("/api/users/me/password", headers=headers, json=body)
    assert response.status_code == 400
    assert response.json()["details"][0]["field"] == "new_password"


@EXTRA
def test_officer_deactivates_user(client, db, signup, officer):
    headers, customer_id = signup()
    url = f"/api/users/{user_id(db, 'meena')}"
    response = client.delete(url, headers=officer)
    assert response.status_code == 200
    assert response.json() == {"message": "User deactivated successfully"}
    # Soft delete: the row and the customer profile stay, logging in does not work.
    assert client.get(url, headers=officer).json()["is_active"] is False
    assert client.get(f"/api/customers/{customer_id}", headers=officer).is_success
    assert client.get("/api/customers/me", headers=headers).status_code == 401
    form = {"username": "meena", "password": PASSWORD}
    response = client.post("/auth/login", data=form)
    assert response.status_code == 401
    assert error_of(response) == "INVALID_CREDENTIALS"


@EXTRA
def test_deactivate_rules(client, db, signup, officer):
    headers, _ = signup()
    signup(email="ravi@example.com")
    ravi = f"/api/users/{user_id(db, 'ravi')}"
    assert client.delete(ravi, headers=headers).status_code == 403
    own = client.delete(f"/api/users/{user_id(db, 'officer1')}", headers=officer)
    assert own.status_code == 403 and error_of(own) == "CANNOT_DEACTIVATE_SELF"
    assert client.delete("/api/users/999999", headers=officer).status_code == 404


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


@EXTRA
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/customers"),
        ("delete", "/api/customers/1"),
        ("delete", "/api/loans/1"),
        ("get", "/api/users"),
        ("patch", "/api/users/1/role"),
        ("delete", "/api/users/1"),
    ],
)
def test_customer_on_officer_route_is_403(client, signup, method, path):
    headers, _ = signup()
    body = {**PROFILE, "email": "x@example.com", "role": "OFFICER"}
    response = client.request(method, path, headers=headers, json=body)
    assert response.status_code == 403


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
