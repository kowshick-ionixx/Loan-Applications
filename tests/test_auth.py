from datetime import UTC, datetime, timedelta

import jwt
import pytest
from conftest import PASSWORD, PROFILE, apply, login, register

from loan_application.config import settings
from loan_application.logging_config import LogContextFilter
from loan_application.models import User


def error_of(response):
    return response.json()["error"]


def customer_id_of(db, username):
    return db.query(User).filter_by(username=username).one().customer_id


def test_register_creates_customer_without_profile(client, db):
    response = register(client, "Meena.Das")
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "meena.das"
    assert body["role"] == "CUSTOMER"
    assert body["has_customer_profile"] is False
    assert PASSWORD not in response.text and "password" not in body
    assert db.get(User, body["id"]).password_hash != PASSWORD


def test_register_duplicate_username(client):
    register(client, "meena")
    response = register(client, "MEENA")
    assert response.status_code == 409
    assert error_of(response) == "DUPLICATE_USERNAME"


def test_register_lists_every_invalid_field(client):
    response = client.post(
        "/auth/register", json={"username": "a!", "password": "short"}
    )
    assert response.status_code == 400
    assert error_of(response) == "VALIDATION_FAILED"
    fields = {d["field"] for d in response.json()["details"]}
    assert fields == {"username", "password"}


def test_register_ignores_role_in_body(client):
    body = {"username": "sneaky", "password": PASSWORD, "role": "OFFICER"}
    assert client.post("/auth/register", json=body).json()["role"] == "CUSTOMER"


def test_login_success_is_case_insensitive(client):
    register(client, "meena")
    login(client, "MEENA")


@pytest.mark.parametrize(
    ("username", "password"), [("meena", "wrong-password"), ("nobody", PASSWORD)]
)
def test_login_wrong_username_or_password(client, username, password):
    register(client, "meena")
    response = client.post(
        "/auth/login", data={"username": username, "password": password}
    )
    assert response.status_code == 401
    assert error_of(response) == "INVALID_CREDENTIALS"


def test_login_inactive_user(client, db):
    register(client, "meena")
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
def test_customer_without_profile_gets_403(client, method, path):
    register(client, "meena")
    headers = login(client, "meena")
    body = {**PROFILE, "customer_id": 1, "amount": 100000, "tenure_months": 12}
    response = client.request(method, path, headers=headers, json=body)
    assert response.status_code == 403
    assert error_of(response) == "CUSTOMER_PROFILE_REQUIRED"


def test_create_profile_links_user_and_only_once(client, db):
    register(client, "meena")
    headers = login(client, "meena")
    created = client.post("/api/customers", headers=headers, json=PROFILE)
    assert created.status_code == 201
    assert customer_id_of(db, "meena") == created.json()["id"]
    again = client.post("/api/customers", headers=headers, json=PROFILE)
    assert again.status_code == 409
    assert error_of(again) == "PROFILE_ALREADY_EXISTS"


def test_profile_with_taken_email_is_not_linked(client, db, officer):
    client.post("/api/customers", headers=officer, json=PROFILE)
    register(client, "meena")
    headers = login(client, "meena")
    response = client.post("/api/customers", headers=headers, json=PROFILE)
    assert error_of(response) == "DUPLICATE_EMAIL"
    assert customer_id_of(db, "meena") is None


def test_officer_creates_customer_without_link(client, db, officer):
    response = client.post("/api/customers", headers=officer, json=PROFILE)
    assert response.status_code == 201
    assert customer_id_of(db, "officer1") is None


def test_customer_only_reaches_own_data(client, signup, officer):
    headers_a, a = signup(email="asha@example.com")
    _, b = signup(email="bala@example.com")
    loan_b = apply(client, officer, b).json()["id"]

    for path in (
        f"/api/customers/{b}",
        f"/api/customers/{b}/summary",
        f"/api/customers/{b}/loans",
        f"/api/loans/{loan_b}",
        "/api/customers/999999",
        "/api/loans/999999",
    ):
        response = client.get(path, headers=headers_a)
        assert response.status_code == 403, path
        assert error_of(response) == "FORBIDDEN"
    assert client.get(f"/api/customers/{a}", headers=headers_a).status_code == 200


def test_customer_cannot_apply_for_another_customer(client, signup):
    headers_a, a = signup(email="asha@example.com")
    _, b = signup(email="bala@example.com")
    assert apply(client, headers_a, b).status_code == 403
    assert apply(client, headers_a, a).status_code == 201


def test_officer_reaches_everything(client, signup, officer):
    _, cid = signup()
    loan = apply(client, officer, cid).json()["id"]
    for path in (
        f"/api/customers/{cid}",
        f"/api/customers/{cid}/summary",
        f"/api/customers/{cid}/loans",
        f"/api/loans/{loan}",
    ):
        assert client.get(path, headers=officer).status_code == 200, path
    assert client.get("/api/customers/999999", headers=officer).status_code == 404


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
