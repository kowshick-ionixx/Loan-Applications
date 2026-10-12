import pytest

CUSTOMER = {
    "name": "Ravi Kumar",
    "email": "Ravi@Example.com",
    "phone": "9876543210",
    "date_of_birth": "1990-05-15",
    "monthly_income": 50000,
}


@pytest.fixture
def customer(client):
    response = client.post("/api/customers", json=CUSTOMER)
    assert response.status_code == 201
    return response.json()


def apply(client, customer_id, amount=300000, tenure_months=36):
    return client.post(
        "/api/loans",
        json={
            "customer_id": customer_id,
            "amount": amount,
            "tenure_months": tenure_months,
        },
    )


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]


def test_request_id_is_echoed(client):
    response = client.get("/health", headers={"X-Request-ID": "abc123"})
    assert response.headers["X-Request-ID"] == "abc123"


# ---------- customers ----------


def test_create_customer(customer):
    assert customer["id"] > 0
    assert customer["email"] == "ravi@example.com"
    assert customer["monthly_income"] == 50000


def test_get_customer(client, customer):
    response = client.get(f"/api/customers/{customer['id']}")
    assert response.status_code == 200
    assert response.json() == customer


def test_get_missing_customer(client):
    response = client.get("/api/customers/999999")
    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "NOT_FOUND"
    assert body["message"] == "Customer with id 999999 not found"
    assert body["request_id"]


def test_duplicate_email(client, customer):
    response = client.post(
        "/api/customers", json={**CUSTOMER, "email": "RAVI@example.com"}
    )
    assert response.status_code == 409
    assert response.json()["error"] == "DUPLICATE_EMAIL"


def test_update_customer(client, customer):
    data = {**CUSTOMER, "name": "Ravi Sharma", "monthly_income": 80000}
    response = client.put(f"/api/customers/{customer['id']}", json=data)
    assert response.status_code == 200
    assert response.json()["name"] == "Ravi Sharma"
    assert response.json()["monthly_income"] == 80000


def test_update_to_duplicate_email(client, customer):
    other = client.post(
        "/api/customers", json={**CUSTOMER, "email": "other@example.com"}
    ).json()
    response = client.put(f"/api/customers/{other['id']}", json=CUSTOMER)
    assert response.status_code == 409
    assert response.json()["error"] == "DUPLICATE_EMAIL"


def test_update_missing_customer(client):
    response = client.put("/api/customers/999999", json=CUSTOMER)
    assert response.status_code == 404


def test_delete_customer(client, customer):
    response = client.delete(f"/api/customers/{customer['id']}")
    assert response.status_code == 200
    assert response.json() == customer
    assert client.get(f"/api/customers/{customer['id']}").status_code == 404


def test_delete_customer_with_loans(client, customer):
    apply(client, customer["id"])
    response = client.delete(f"/api/customers/{customer['id']}")
    assert response.status_code == 409
    assert response.json()["error"] == "CUSTOMER_HAS_LOANS"
    assert client.get(f"/api/customers/{customer['id']}").status_code == 200


@pytest.mark.parametrize(
    "field, value",
    [
        ("name", "Ab"),
        ("name", "R4vi"),
        ("name", " Ravi"),
        ("email", "not-an-email"),
        ("phone", "12345"),
        ("phone", "98765432ab"),
        ("date_of_birth", "2999-01-01"),
        ("date_of_birth", "15-05-1990"),
        ("monthly_income", 0),
        ("monthly_income", -100),
        ("monthly_income", 100.123),
    ],
)
def test_invalid_customer_fields(client, field, value):
    response = client.post("/api/customers", json={**CUSTOMER, field: value})
    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "VALIDATION_FAILED"
    assert [d["field"] for d in body["details"]] == [field]


def test_missing_customer_field(client):
    data = {k: v for k, v in CUSTOMER.items() if k != "phone"}
    response = client.post("/api/customers", json=data)
    assert response.status_code == 400
    assert response.json()["details"] == [{"field": "phone", "message": "is required"}]


@pytest.mark.parametrize("body", ["", "{bad json", "[]"])
def test_invalid_json_body(client, body):
    response = client.post(
        "/api/customers",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert response.json()["error"] in ("INVALID_REQUEST", "VALIDATION_FAILED")


@pytest.mark.parametrize("bad_id", ["0", "-1", "abc", "2147483648"])
def test_invalid_customer_id_in_path(client, bad_id):
    response = client.get(f"/api/customers/{bad_id}")
    assert response.status_code == 400
    assert response.json()["details"][0]["field"] == "customer_id"


# ---------- loans ----------


def test_loan_approved(client, customer):
    response = apply(client, customer["id"], amount=300000, tenure_months=36)
    assert response.status_code == 201
    loan = response.json()
    assert loan["status"] == "APPROVED"
    assert loan["emi"] == 9964.29
    assert loan["interest_rate"] == 12
    assert loan["rejection_reason"] is None


def test_loan_rejected_income(client, customer):
    response = apply(client, customer["id"], amount=1000001)
    assert response.status_code == 201
    loan = response.json()
    assert loan["status"] == "REJECTED"
    assert loan["emi"] is None
    assert loan["rejection_reason"] == "Requested amount exceeds 20x monthly income"


def test_loan_rejected_age(client):
    young = client.post(
        "/api/customers",
        json={**CUSTOMER, "email": "young@example.com", "date_of_birth": "2010-01-01"},
    ).json()
    loan = apply(client, young["id"]).json()
    assert loan["status"] == "REJECTED"
    assert loan["rejection_reason"] == "Age must be between 21 and 60"


def test_third_loan_rejected(client, customer):
    assert apply(client, customer["id"]).json()["status"] == "APPROVED"
    assert apply(client, customer["id"]).json()["status"] == "APPROVED"
    loan = apply(client, customer["id"]).json()
    assert loan["status"] == "REJECTED"
    assert loan["rejection_reason"] == "Customer already has 2 active loans"


def test_get_loan(client, customer):
    loan = apply(client, customer["id"]).json()
    response = client.get(f"/api/loans/{loan['id']}")
    assert response.status_code == 200
    assert response.json() == loan


def test_get_missing_loan(client):
    response = client.get("/api/loans/999999")
    assert response.status_code == 404
    assert response.json()["message"] == "Loan with id 999999 not found"


def test_loan_for_missing_customer(client):
    response = apply(client, 999999)
    assert response.status_code == 404


@pytest.mark.parametrize(
    "field, value",
    [
        ("customer_id", 0),
        ("customer_id", "1"),
        ("amount", 9999.99),
        ("amount", 5000000.01),
        ("amount", 10000.001),
        ("tenure_months", 18),
    ],
)
def test_invalid_loan_fields(client, field, value):
    data = {"customer_id": 1, "amount": 300000, "tenure_months": 36, field: value}
    response = client.post("/api/loans", json=data)
    assert response.status_code == 400
    assert [d["field"] for d in response.json()["details"]] == [field]


def test_list_customer_loans(client, customer):
    approved = apply(client, customer["id"]).json()
    rejected = apply(client, customer["id"], amount=2000000).json()

    response = client.get(f"/api/customers/{customer['id']}/loans")
    assert response.status_code == 200
    assert [loan["id"] for loan in response.json()] == [rejected["id"], approved["id"]]

    approved_only = client.get(
        f"/api/customers/{customer['id']}/loans", params={"status": "APPROVED"}
    ).json()
    assert [loan["id"] for loan in approved_only] == [approved["id"]]


def test_list_loans_invalid_status(client, customer):
    response = client.get(
        f"/api/customers/{customer['id']}/loans", params={"status": "PENDING"}
    )
    assert response.status_code == 400
    assert response.json()["details"][0]["field"] == "status"


def test_list_loans_missing_customer(client):
    assert client.get("/api/customers/999999/loans").status_code == 404


def test_summary(client, customer):
    apply(client, customer["id"], amount=300000, tenure_months=36)
    apply(client, customer["id"], amount=100000, tenure_months=12)
    apply(client, customer["id"], amount=100000, tenure_months=12)

    response = client.get(f"/api/customers/{customer['id']}/summary")
    assert response.status_code == 200
    assert response.json() == {
        "customer_id": customer["id"],
        "name": "Ravi Kumar",
        "total_loans": 3,
        "approved_loans": 2,
        "rejected_loans": 1,
        "total_approved_amount": 400000,
        "total_monthly_emi": 18755.88,
    }


def test_summary_no_loans(client, customer):
    body = client.get(f"/api/customers/{customer['id']}/summary").json()
    assert body["total_loans"] == 0
    assert body["total_approved_amount"] == 0
    assert body["total_monthly_emi"] == 0


# ---------- generic errors ----------


def test_unknown_route(client):
    response = client.get("/api/nope")
    assert response.status_code == 404
    assert response.json()["error"] == "NOT_FOUND"


def test_method_not_allowed(client):
    response = client.patch("/api/loans")
    assert response.status_code == 405
    assert response.json()["error"] == "METHOD_NOT_ALLOWED"
