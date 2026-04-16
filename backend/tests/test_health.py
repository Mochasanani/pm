from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_200():
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_returns_ok_status():
    response = client.get("/api/health")
    assert response.json() == {"status": "ok"}


def test_root_serves_placeholder():
    response = client.get("/")
    assert response.status_code == 200
    assert "Kanban Studio" in response.text
