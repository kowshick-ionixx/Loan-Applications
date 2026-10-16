"""Loan rules (EMI, eligibility, risk band) and the loan endpoints."""

from datetime import date, datetime
from decimal import Decimal

import pytest
from conftest import PROFILE, apply, create, fields_of

from loan_application.models import Customer
from loan_application.services.loan_service import (
    INTEREST_RATES,
    calculate_emi,
    check_eligibility,
    get_risk_band,
)

AGE_REASON = "Age must be between 21 and 60"


INCOME_REASON = "Requested amount exceeds 20x monthly income"


ACTIVE_REASON = "Customer already has 2 active loans"


def born_years_ago(years: int) -> str:
    today = datetime.now().astimezone().date()
    try:
        return today.replace(year=today.year - years).isoformat()
    except ValueError:
        return today.replace(day=28, year=today.year - years).isoformat()


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


def test_list_loans_oldest_first_and_status_filter(client, officer):
    cid = create(client, officer)
    first = apply(client, officer, cid).json()["id"]
    second = apply(client, officer, cid, amount=2000000).json()["id"]
    url = f"/api/customers/{cid}/loans"
    listed = client.get(url, headers=officer).json()
    assert [loan["id"] for loan in listed] == [first, second]
    rejected = client.get(f"{url}?status=REJECTED", headers=officer).json()
    assert [loan["id"] for loan in rejected] == [second]
    assert client.get(f"{url}?status=PENDING", headers=officer).status_code == 400
    assert client.get("/api/customers/999999/loans", headers=officer).status_code == 404


def test_list_loans_empty(client, officer):
    cid = create(client, officer)
    response = client.get(f"/api/customers/{cid}/loans", headers=officer)
    assert response.status_code == 200 and response.json() == []


def test_customer_cannot_apply_for_another_customer(client, signup):
    headers_a, a = signup(email="asha@example.com")
    _, b = signup(email="bala@example.com")
    assert apply(client, headers_a, b).status_code == 403
    assert apply(client, headers_a, a).status_code == 201


def ids(response):
    return [loan["id"] for loan in response.json()["items"]]


def test_list_loans_officer_sees_all_customer_sees_own(client, signup, officer):
    meena, meena_id = signup()
    ravi, ravi_id = signup(email="ravi@example.com")
    apply(client, meena, meena_id)
    apply(client, ravi, ravi_id)

    all_loans = client.get("/api/loans", headers=officer).json()["items"]
    assert {loan["customer_id"] for loan in all_loans} == {meena_id, ravi_id}

    own = client.get("/api/loans", headers=meena).json()
    assert [loan["customer_id"] for loan in own["items"]] == [meena_id]
    assert own["total"] == 1


def test_list_loans_filters_by_status(client, signup, officer):
    headers, customer_id = signup()
    apply(client, headers, customer_id)
    apply(client, headers, customer_id, amount=5000000)

    response = client.get("/api/loans?status=REJECTED", headers=officer)
    assert [loan["status"] for loan in response.json()["items"]] == ["REJECTED"]
    assert response.json()["total"] == 1


def test_list_loans_pages_oldest_first(client, officer):
    cid = create(client, officer)
    created = [
        apply(client, officer, cid, amount=2000000).json()["id"] for _ in range(5)
    ]
    first = client.get("/api/loans?page=1&size=2", headers=officer)
    assert first.status_code == 200
    assert first.json() | {"items": None} == {
        "items": None,
        "page": 1,
        "size": 2,
        "total": 5,
        "pages": 3,
    }
    assert ids(first) == created[:2]
    assert ids(client.get("/api/loans?page=2&size=2", headers=officer)) == created[2:4]
    assert ids(client.get("/api/loans?page=3&size=2", headers=officer)) == created[4:]


def test_list_loans_page_past_the_end_is_empty(client, officer):
    cid = create(client, officer)
    apply(client, officer, cid)
    response = client.get("/api/loans?page=9", headers=officer)
    assert response.status_code == 200
    body = response.json()
    assert (body["items"], body["total"], body["pages"]) == ([], 1, 1)


def test_list_loans_defaults_and_no_loans(client, officer):
    body = client.get("/api/loans", headers=officer).json()
    assert body == {"items": [], "page": 1, "size": 20, "total": 0, "pages": 0}


def test_list_loans_status_and_paging_combine(client, signup, officer):
    headers, customer_id = signup()
    approved = apply(client, headers, customer_id).json()["id"]
    rejected = [
        apply(client, headers, customer_id, amount=5000000).json()["id"]
        for _ in range(3)
    ]
    response = client.get("/api/loans?status=REJECTED&size=2&page=2", headers=headers)
    assert ids(response) == [rejected[2]]
    assert (response.json()["total"], response.json()["pages"]) == (3, 2)
    assert approved not in ids(response)


@pytest.mark.parametrize(
    ("query", "field"),
    [
        ("page=0", "page"),
        ("page=-1", "page"),
        ("page=abc", "page"),
        ("size=0", "size"),
        ("size=101", "size"),
        ("status=PENDING", "status"),
    ],
)
def test_list_loans_rejects_bad_query(client, officer, query, field):
    response = client.get(f"/api/loans?{query}", headers=officer)
    assert response.status_code == 400
    assert response.json()["error"] == "VALIDATION_FAILED"
    assert fields_of(response) == {field}


def test_list_loans_needs_login_and_profile(client, profileless):
    assert client.get("/api/loans").status_code == 401
    assert client.get("/api/loans", headers=profileless).status_code == 403


ANITHA = {**PROFILE, "name": "Anitha Selvam", "email": "anitha@example.com"}


RAVI = {**PROFILE, "name": "Ravi Kumar", "email": "ravi@example.com"}


def test_customer_journey(client, officer, signup):
    anitha, cid = signup(**ANITHA)

    blocked = client.post("/api/customers", headers=anitha, json=RAVI)
    assert blocked.status_code == 409
    assert client.get(f"/api/customers/{cid}", headers=anitha).status_code == 200

    approved = apply(client, anitha, cid, amount=300000, tenure_months=36).json()
    assert approved["status"] == "APPROVED" and approved["emi"] == 9964.29
    rejected = apply(client, anitha, cid, amount=2000000, tenure_months=36).json()
    assert rejected["status"] == "REJECTED"
    assert rejected["rejection_reason"] == "Requested amount exceeds 20x monthly income"

    loans_url = f"/api/customers/{cid}/loans"
    loans = client.get(loans_url, headers=anitha).json()
    assert [loan["id"] for loan in loans] == [approved["id"], rejected["id"]]
    pending = client.get(f"{loans_url}?status=PENDING", headers=anitha)
    assert pending.status_code == 400

    summary_url = f"/api/customers/{cid}/summary"
    summary = client.get(summary_url, headers=anitha).json()
    assert summary["total_applications"] == 2
    assert summary["approved_count"] == 1 and summary["rejected_count"] == 1
    assert summary["total_approved_amount"] == 300000
    assert summary["total_monthly_emi"] == 9964.29
    assert summary["emi_to_income_ratio"] == 19.93
    assert summary["risk_band"] == "LOW"

    ravi, _ = signup(**RAVI)

    anithas_things = [
        f"/api/customers/{cid}",
        f"/api/loans/{approved['id']}",
        loans_url,
        summary_url,
    ]
    for path in anithas_things:
        assert client.get(path, headers=ravi).status_code == 403, path
    assert apply(client, ravi, cid).status_code == 403

    for path in anithas_things:
        assert client.get(path, headers=officer).status_code == 200, path

    assert client.get(summary_url).status_code == 401
    bad_token = {"Authorization": "Bearer not-a-jwt"}
    assert client.get(summary_url, headers=bad_token).status_code == 401


TODAY = date(2026, 10, 8)


def make_customer(age: int = 30, income: str = "50000") -> Customer:
    dob = date(TODAY.year - age, TODAY.month, TODAY.day)
    return Customer(date_of_birth=dob, monthly_income=Decimal(income))


def test_emi_spec_example():
    assert calculate_emi(Decimal(300000), Decimal(12), 36) == Decimal("9964.29")


@pytest.mark.parametrize(
    ("months", "rate", "expected_emi"),
    [
        (12, 10, "8791.59"),
        (24, 11, "4660.78"),
        (36, 12, "3321.43"),
        (48, 13, "2682.75"),
        (60, 13, "2275.31"),
    ],
)
def test_rate_and_emi_for_each_tenure(months, rate, expected_emi):
    assert INTEREST_RATES[months] == rate
    emi = calculate_emi(Decimal(100000), INTEREST_RATES[months], months)
    assert emi == Decimal(expected_emi)


@pytest.mark.parametrize(
    ("age", "expected"),
    [(19, AGE_REASON), (20, AGE_REASON), (21, None), (60, None), (61, AGE_REASON)],
)
def test_age_rule(age, expected):
    customer = make_customer(age=age)
    assert check_eligibility(customer, Decimal(100000), 0, TODAY) == expected


@pytest.mark.parametrize(
    ("amount", "income", "expected"),
    [
        ("1000000", "50000", None),
        ("1000001", "50000", INCOME_REASON),
        ("1000000", "40000", INCOME_REASON),
    ],
)
def test_income_rule(amount, income, expected):
    customer = make_customer(income=income)
    assert check_eligibility(customer, Decimal(amount), 0, TODAY) == expected


@pytest.mark.parametrize(
    ("approved_count", "expected"), [(0, None), (1, None), (2, ACTIVE_REASON)]
)
def test_active_loans_rule(approved_count, expected):
    customer = make_customer()
    result = check_eligibility(customer, Decimal(100000), approved_count, TODAY)
    assert result == expected


def test_first_failing_rule_wins():
    young_and_poor = make_customer(age=20, income="10000")
    assert check_eligibility(young_and_poor, Decimal(5000000), 2, TODAY) == AGE_REASON
    poor = make_customer(income="10000")
    assert check_eligibility(poor, Decimal(5000000), 2, TODAY) == INCOME_REASON


@pytest.mark.parametrize(
    ("ratio", "band"),
    [
        ("0", "LOW"),
        ("29.99", "LOW"),
        ("30", "MEDIUM"),
        ("50", "MEDIUM"),
        ("50.01", "HIGH"),
    ],
)
def test_risk_band(ratio, band):
    assert get_risk_band(Decimal(ratio)) == band
