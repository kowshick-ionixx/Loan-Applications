"""Customer endpoints: create, read, summary."""

import pytest
from conftest import PROFILE, apply, create, error_of, fields_of

from loan_application.models import User
from loan_application.services import customer_service


def test_create_and_get_customer(client, officer):
    response = client.post("/api/customers", headers=officer, json=PROFILE)
    assert response.status_code == 201
    created = response.json()
    assert created == {**PROFILE, "address": None, "id": created["id"]}
    fetched = client.get(f"/api/customers/{created['id']}", headers=officer)
    assert fetched.status_code == 200 and fetched.json() == created


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", "A1"),
        ("phone", "98765"),
        ("date_of_birth", "2999-01-01"),
        ("monthly_income", 0),
    ],
)
def test_customer_field_rules(client, officer, field, value):
    body = {**PROFILE, field: value}
    response = client.post("/api/customers", headers=officer, json=body)
    assert response.status_code == 400
    assert response.json()["error"] == "VALIDATION_FAILED"
    assert fields_of(response) == {field}


def test_all_failing_fields_are_listed(client, officer):
    body = {**PROFILE, "email": "not-an-email", "phone": "98765"}
    response = client.post("/api/customers", headers=officer, json=body)
    assert response.status_code == 400
    assert fields_of(response) == {"email", "phone"}


def test_duplicate_email(client, officer):
    create(client, officer)
    response = client.post("/api/customers", headers=officer, json=PROFILE)
    assert response.status_code == 409
    assert response.json()["error"] == "DUPLICATE_EMAIL"


@pytest.mark.parametrize("raw", ['{"name": "Broken",', ""])
def test_malformed_or_empty_json(client, officer, raw):
    headers = {**officer, "Content-Type": "application/json"}
    response = client.post("/api/customers", headers=headers, content=raw)
    assert response.status_code == 400
    assert response.json()["error"] == "INVALID_REQUEST"


def test_missing_customer_is_404(client, officer):
    response = client.get("/api/customers/999", headers=officer)
    assert response.status_code == 404
    assert response.json()["error"] == "NOT_FOUND"
    assert response.json()["message"] == "Customer with id 999 not found"


@pytest.mark.parametrize("path", ["/api/customers/abc", "/api/customers/0"])
def test_bad_customer_id_is_400(client, officer, path):
    assert client.get(path, headers=officer).status_code == 400


def test_summary_with_no_loans(client, officer):
    cid = create(client, officer)
    summary = client.get(f"/api/customers/{cid}/summary", headers=officer).json()
    assert summary == {
        "customer_id": cid,
        "customer_name": PROFILE["name"],
        "total_applications": 0,
        "approved_count": 0,
        "rejected_count": 0,
        "total_approved_amount": 0,
        "total_monthly_emi": 0,
        "emi_to_income_ratio": 0,
        "risk_band": "LOW",
    }


def test_summary_counts_approved_only(client, officer):
    cid = create(client, officer)
    apply(client, officer, cid, amount=300000, tenure_months=36)
    apply(client, officer, cid, amount=200000, tenure_months=24)
    apply(client, officer, cid)
    summary = client.get(f"/api/customers/{cid}/summary", headers=officer).json()
    assert summary["total_applications"] == 3
    assert summary["approved_count"] == 2 and summary["rejected_count"] == 1
    assert summary["total_approved_amount"] == 500000
    assert summary["total_monthly_emi"] == 19285.86
    assert summary["emi_to_income_ratio"] == 38.57
    assert summary["risk_band"] == "MEDIUM"
    response = client.get("/api/customers/999999/summary", headers=officer)
    assert response.status_code == 404


def test_unexpected_error_is_500_without_stack_trace(client, officer, monkeypatch):
    def boom(*args):
        raise RuntimeError("database exploded")

    monkeypatch.setattr(customer_service, "get_customer", boom)
    response = client.get("/api/customers/1", headers=officer)
    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "INTERNAL_ERROR" and body["request_id"]
    assert "exploded" not in response.text and "Traceback" not in response.text


def customer_id_of(db, username):
    return db.query(User).filter_by(username=username).one().customer_id


def test_customer_creates_own_profile_once(client, db, profileless):
    response = client.post("/api/customers", headers=profileless, json=PROFILE)
    assert response.status_code == 201
    assert customer_id_of(db, "noprofile") == response.json()["id"]
    other = {**PROFILE, "email": "other@example.com"}
    response = client.post("/api/customers", headers=profileless, json=other)
    assert response.status_code == 409
    assert error_of(response) == "PROFILE_EXISTS"


def test_customer_with_profile_cannot_create_another(client, signup):
    headers, _ = signup()
    other = {**PROFILE, "email": "other@example.com"}
    response = client.post("/api/customers", headers=headers, json=other)
    assert response.status_code == 409
    assert error_of(response) == "PROFILE_EXISTS"


def test_customer_profile_with_taken_email_is_not_linked(
    client, db, officer, profileless
):
    create(client, officer)
    response = client.post("/api/customers", headers=profileless, json=PROFILE)
    assert response.status_code == 409
    assert error_of(response) == "DUPLICATE_EMAIL"
    assert customer_id_of(db, "noprofile") is None


def test_officer_creates_customer_without_link(client, db, officer):
    response = client.post("/api/customers", headers=officer, json=PROFILE)
    assert response.status_code == 201
    assert customer_id_of(db, "officer1") is None


def test_officer_creates_profile_linked_to_a_customer_login(
    client, db, officer, profileless
):
    body = {**PROFILE, "username": "NoProfile"}
    response = client.post("/api/customers", headers=officer, json=body)
    assert response.status_code == 201
    assert "username" not in response.json()
    assert customer_id_of(db, "noprofile") == response.json()["id"]
    assert customer_id_of(db, "officer1") is None
    summary = f"/api/customers/{response.json()['id']}/summary"
    assert client.get(summary, headers=profileless).status_code == 200


def test_officer_cannot_link_a_login_that_has_a_profile(client, db, officer, signup):
    _, customer_id = signup()
    body = {**PROFILE, "email": "other@example.com", "username": "meena"}
    response = client.post("/api/customers", headers=officer, json=body)
    assert response.status_code == 409
    assert error_of(response) == "PROFILE_EXISTS"
    assert customer_id_of(db, "meena") == customer_id


@pytest.mark.parametrize(
    ("username", "status", "error"),
    [("ghost", 404, "NOT_FOUND"), ("officer1", 400, "NOT_A_CUSTOMER")],
)
def test_officer_link_needs_an_existing_customer_login(
    client, officer, username, status, error
):
    body = {**PROFILE, "username": username}
    response = client.post("/api/customers", headers=officer, json=body)
    assert response.status_code == status
    assert error_of(response) == error
    create(client, officer)


def test_customer_cannot_link_their_profile_to_another_login(
    client, db, profileless, signup
):
    signup(email="asha@example.com")
    body = {**PROFILE, "username": "asha"}
    response = client.post("/api/customers", headers=profileless, json=body)
    assert response.status_code == 201
    assert customer_id_of(db, "noprofile") == response.json()["id"]
    assert customer_id_of(db, "asha") != response.json()["id"]


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
