from conftest import PROFILE, apply, login, register

ANITHA = {**PROFILE, "name": "Anitha Selvam", "email": "anitha@example.com"}
RAVI = {**PROFILE, "name": "Ravi Kumar", "email": "ravi@example.com"}


def test_customer_journey(client, officer):
    assert register(client, "anitha").status_code == 201
    anitha = login(client, "anitha")

    blocked = apply(client, anitha, 1)
    assert blocked.status_code == 403
    assert blocked.json()["error"] == "CUSTOMER_PROFILE_REQUIRED"

    created = client.post("/api/customers", headers=anitha, json=ANITHA)
    assert created.status_code == 201
    cid = created.json()["id"]
    again = client.post("/api/customers", headers=anitha, json=ANITHA)
    assert again.status_code == 409
    assert again.json()["error"] == "PROFILE_ALREADY_EXISTS"

    approved = apply(client, anitha, cid, amount=300000, tenure_months=36).json()
    assert approved["status"] == "APPROVED" and approved["emi"] == 9964.29
    rejected = apply(client, anitha, cid, amount=2000000, tenure_months=36).json()
    assert rejected["status"] == "REJECTED"
    assert rejected["rejection_reason"] == "Requested amount exceeds 20x monthly income"

    loans_url = f"/api/customers/{cid}/loans"
    loans = client.get(loans_url, headers=anitha).json()
    assert [loan["id"] for loan in loans] == [rejected["id"], approved["id"]]
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

    register(client, "ravi")
    ravi = login(client, "ravi")
    assert client.post("/api/customers", headers=ravi, json=RAVI).status_code == 201

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
