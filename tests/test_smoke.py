from fastapi.testclient import TestClient

from loan_application.main import app

client = TestClient(app)


def test_docs_page_loads():
    response = client.get("/docs")
    assert response.status_code == 200


def test_customer_endpoint_needs_token():
    response = client.get("/customers/9999")
    assert response.status_code == 401
    assert response.json()["error"] == "UNAUTHORIZED"
