def test_health_returns_200(client):
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_returns_ok_status(client):
    response = client.get("/api/health")
    assert response.json() == {"status": "ok"}


def test_root_serves_placeholder(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Kanban Studio" in response.text
