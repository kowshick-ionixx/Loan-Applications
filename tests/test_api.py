from datetime import datetime

import pytest
from conftest import PROFILE, apply

from loan_application.services import customer_service

AGE_REASON = "Age must be between 21 and 60"
INCOME_REASON = "Requested amount exceeds 20x monthly income"
ACTIVE_REASON = "Customer already has 2 active loans"


def born_years_ago(years: int) -> str:
    today = datetime.now().astimezone().date()
    try:
        return today.replace(year=today.year - years).isoformat()
    except ValueError:  # 29 Feb in a non-leap year
        return today.replace(day=28, year=today.year - years).isoformat()


def create(client, officer, **fields):
    response = client.post(
        "/api/customers", headers=officer, json={**PROFILE, **fields}
    )
    assert response.status_code == 201, response.json()
    return response.json()["id"]


def fields_of(response):
    return {d["field"] for d in response.json()["details"]}


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_create_and_get_customer(client, officer):
    response = client.post("/api/customers", headers=officer, json=PROFILE)
    assert response.status_code == 201
    created = response.json()
    assert created == {**PROFILE, "id": created["id"]}
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
def test_bad_id_is_400(client, officer, path):
    assert client.get(path, headers=officer).status_code == 400


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"amount": 5000, "tenure_months": 36}, "amount"),
        ({"amount": 300000, "tenure_months": 18}, "tenure_months"),
    ],
)
def test_loan_field_rules(client, officer, body, field):
    cid = create(client, officer)
    response = client.post(
        "/api/loans", headers=officer, json={"customer_id": cid, **body}
    )
    assert response.status_code == 400
    assert fields_of(response) == {field}


def test_loan_for_missing_customer_is_404(client, officer):
    assert apply(client, officer, 999999).status_code == 404


def test_approved_loan_matches_spec_example(client, officer):
    cid = create(client, officer)
    response = apply(client, officer, cid, amount=300000, tenure_months=36)
    assert response.status_code == 201
    loan = response.json()
    assert loan["status"] == "APPROVED"
    assert loan["interest_rate"] == 12.0 and loan["emi"] == 9964.29
    assert loan["rejection_reason"] is None
    assert loan["applied_on"] == datetime.now().astimezone().date().isoformat()
    fetched = client.get(f"/api/loans/{loan['id']}", headers=officer)
    assert fetched.status_code == 200 and fetched.json() == loan


@pytest.mark.parametrize(
    ("customer", "amount", "reason"),
    [
        ({"date_of_birth": born_years_ago(19)}, 100000, AGE_REASON),
        ({"monthly_income": 40000}, 1000000, INCOME_REASON),
    ],
)
def test_rejected_loan_is_saved_with_reason(client, officer, customer, amount, reason):
    cid = create(client, officer, **customer)
    response = apply(client, officer, cid, amount=amount)
    assert response.status_code == 201
    assert response.json()["status"] == "REJECTED"
    assert response.json()["rejection_reason"] == reason
    assert client.get(f"/api/loans/{response.json()['id']}", headers=officer).is_success


def test_third_loan_after_two_approvals(client, officer):
    cid = create(client, officer)
    apply(client, officer, cid)
    apply(client, officer, cid)
    third = apply(client, officer, cid).json()
    assert third["status"] == "REJECTED"
    assert third["rejection_reason"] == ACTIVE_REASON


def test_list_loans_newest_first_and_status_filter(client, officer):
    cid = create(client, officer)
    first = apply(client, officer, cid).json()["id"]
    second = apply(client, officer, cid, amount=2000000).json()["id"]
    url = f"/api/customers/{cid}/loans"
    listed = client.get(url, headers=officer).json()
    assert [loan["id"] for loan in listed] == [second, first]
    rejected = client.get(f"{url}?status=REJECTED", headers=officer).json()
    assert [loan["id"] for loan in rejected] == [second]
    assert client.get(f"{url}?status=PENDING", headers=officer).status_code == 400
    assert client.get("/api/customers/999999/loans", headers=officer).status_code == 404


def test_list_loans_empty(client, officer):
    cid = create(client, officer)
    response = client.get(f"/api/customers/{cid}/loans", headers=officer)
    assert response.status_code == 200 and response.json() == []


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


def test_request_id_header_and_error_body(client):
    response = client.get("/api/loans/1", headers={"X-Request-ID": "abc123"})
    assert response.headers["X-Request-ID"] == "abc123"
    assert response.json()["request_id"] == "abc123"
