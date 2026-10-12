from fastapi.testclient import TestClient

from loan_application.main import app

client = TestClient(app)


def test_docs_page_loads():
    response = client.get("/docs")
    assert response.status_code == 200


def test_get_missing_customer_returns_404():
    response = client.get("/customers/9999")
    assert response.status_code == 404
    assert response.json() == {
        "error": "NOT_FOUND",
        "message": "Customer with id 9999 not found",
    }
