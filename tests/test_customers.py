"""Customer endpoints: create, read, list, /me, PATCH, delete, summary."""

import pytest
from conftest import EXTRA, PROFILE, apply, create, error_of, fields_of

from loan_application.models import User
from loan_application.repositories import loan_repository
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


@EXTRA
def test_customer_patches_safe_fields_of_own_profile(client, signup):
    headers, customer_id = signup()
    body = {"name": "Meena Kumari", "phone": "9123456780", "address": "Chennai"}
    response = client.patch(f"/api/customers/{customer_id}", headers=headers, json=body)
    assert response.status_code == 200
    assert response.json() == {**PROFILE, **body, "id": customer_id}


@EXTRA
@pytest.mark.parametrize(
    "field",
    [
        ("email", "new@example.com"),
        ("monthly_income", 999999),
        ("date_of_birth", "1980-01-01"),
    ],
    ids=lambda f: f[0],
)
def test_customer_cannot_patch_locked_fields(client, signup, field):
    headers, customer_id = signup()
    url = f"/api/customers/{customer_id}"
    body = {"name": "Meena Kumari", field[0]: field[1]}
    response = client.patch(url, headers=headers, json=body)
    assert response.status_code == 403
    assert field[0] in response.json()["message"]
    # Nothing was saved, not even the allowed field.
    assert client.get(url, headers=headers).json()["name"] == PROFILE["name"]


@EXTRA
def test_customer_id_in_patch_body_is_ignored(client, signup):
    headers, customer_id = signup()
    _, other_id = signup(email="ravi@example.com")
    url = f"/api/customers/{customer_id}"
    body = {"customer_id": other_id, "id": other_id, "name": "Meena Kumari"}
    response = client.patch(url, headers=headers, json=body)
    assert response.status_code == 200
    assert response.json()["id"] == customer_id


@EXTRA
def test_officer_patches_any_field(client, signup, officer):
    _, customer_id = signup()
    body = {"monthly_income": 75000, "email": "meena.new@example.com"}
    url = f"/api/customers/{customer_id}"
    response = client.patch(url, headers=officer, json=body)
    assert response.status_code == 200
    assert response.json()["monthly_income"] == 75000
    assert response.json()["email"] == "meena.new@example.com"


@EXTRA
def test_patch_with_null_required_field_is_400(client, signup):
    headers, customer_id = signup()
    url = f"/api/customers/{customer_id}"
    response = client.patch(url, headers=headers, json={"name": None})
    assert response.status_code == 400
    assert response.json()["details"][0]["field"] == "name"


@EXTRA
def test_customer_cannot_update_another_customer(client, signup):
    meena, _ = signup()
    _, ravi_id = signup(email="ravi@example.com")
    url = f"/api/customers/{ravi_id}"
    response = client.patch(url, headers=meena, json={"name": "Hacked Name"})
    assert response.status_code == 403


@EXTRA
def test_update_with_taken_email_is_409(client, signup, officer):
    signup()
    _, ravi_id = signup(email="ravi@example.com")
    url = f"/api/customers/{ravi_id}"
    body = {"email": PROFILE["email"]}
    response = client.patch(url, headers=officer, json=body)
    assert response.status_code == 409
    assert response.json()["error"] == "DUPLICATE_EMAIL"


@EXTRA
def test_update_missing_customer_is_404(client, officer):
    response = client.patch("/api/customers/999", headers=officer, json={})
    assert response.status_code == 404


@EXTRA
def test_officer_deletes_customer_without_loans(client, officer):
    customer_id = client.post("/api/customers", headers=officer, json=PROFILE).json()[
        "id"
    ]
    response = client.delete(f"/api/customers/{customer_id}", headers=officer)
    assert response.status_code == 200
    assert response.json() == {"message": "Customer deleted successfully"}
    response = client.get(f"/api/customers/{customer_id}", headers=officer)
    assert response.status_code == 404


@EXTRA
def test_customer_with_active_loans_cannot_be_deleted(client, signup, officer):
    headers, customer_id = signup()
    apply(client, headers, customer_id)
    response = client.delete(f"/api/customers/{customer_id}", headers=officer)
    assert response.status_code == 409
    assert response.json()["error"] == "CUSTOMER_HAS_ACTIVE_LOANS"


@EXTRA
def test_customer_with_only_rejected_loans_is_deleted(client, signup, officer):
    headers, customer_id = signup()
    rejected = apply(client, headers, customer_id, amount=5000000).json()
    assert rejected["status"] == "REJECTED"
    response = client.delete(f"/api/customers/{customer_id}", headers=officer)
    assert response.status_code == 200
    assert response.json() == {"message": "Customer deleted successfully"}
    assert (
        client.get(f"/api/loans/{rejected['id']}", headers=officer).status_code == 404
    )


@EXTRA
def test_loan_added_during_delete_is_409_not_500(client, signup, officer, monkeypatch):
    # Simulates an approved loan arriving after the "active loans?" check: the
    # foreign key must turn into 409, and the customer must still exist.
    headers, customer_id = signup()
    apply(client, headers, customer_id)
    monkeypatch.setattr(
        loan_repository, "count_approved_for_customer", lambda db, cid: 0
    )
    response = client.delete(f"/api/customers/{customer_id}", headers=officer)
    assert response.status_code == 409
    assert response.json()["error"] == "CUSTOMER_HAS_ACTIVE_LOANS"
    assert client.get(f"/api/customers/{customer_id}", headers=officer).is_success


@EXTRA
def test_customer_cannot_delete_customer(client, signup):
    headers, customer_id = signup()
    response = client.delete(f"/api/customers/{customer_id}", headers=headers)
    assert response.status_code == 403


@EXTRA
def test_deleting_a_customer_unlinks_their_login(client, signup, officer):
    headers, customer_id = signup()
    response = client.delete(f"/api/customers/{customer_id}", headers=officer)
    assert response.status_code == 200
    response = client.get(f"/api/customers/{customer_id}", headers=headers)
    assert response.status_code == 403
    assert error_of(response) == "CUSTOMER_PROFILE_REQUIRED"


@EXTRA
def test_officer_lists_customers_with_pagination(client, signup, officer):
    ids = [signup(email=f"user{n}@example.com")[1] for n in range(3)]
    first = client.get("/api/customers?page=1&size=2", headers=officer).json()
    assert [c["id"] for c in first["items"]] == ids[:2]
    assert (first["page"], first["size"], first["total"], first["pages"]) == (
        1,
        2,
        3,
        2,
    )
    second = client.get("/api/customers?page=2&size=2", headers=officer).json()
    assert [c["id"] for c in second["items"]] == ids[2:]
    empty = client.get("/api/customers?page=9&size=2", headers=officer).json()
    assert empty["items"] == [] and empty["total"] == 3


@EXTRA
@pytest.mark.parametrize("query", ["page=0", "size=0", "size=101", "page=abc"])
def test_customer_list_rejects_bad_paging(client, officer, query):
    response = client.get(f"/api/customers?{query}", headers=officer)
    assert response.status_code == 400


@EXTRA
def test_customer_cannot_list_customers(client, signup):
    headers, _ = signup()
    response = client.get("/api/customers", headers=headers)
    assert response.status_code == 403
    assert error_of(response) == "FORBIDDEN"


@EXTRA
def test_customer_reads_own_profile_via_me(client, signup):
    headers, customer_id = signup()
    response = client.get("/api/customers/me", headers=headers)
    assert response.status_code == 200
    assert response.json() == {**PROFILE, "address": None, "id": customer_id}


@EXTRA
@pytest.mark.parametrize("who", ["officer", "profileless"])
def test_me_without_profile_is_404(client, request, who):
    response = client.get("/api/customers/me", headers=request.getfixturevalue(who))
    assert response.status_code == 404
    assert error_of(response) == "NOT_FOUND"
