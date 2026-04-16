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


def test_lifespan_initializes_db(test_db):
    """Exercising the app lifespan should create the users table."""
    import sqlite3
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app):
        pass

    conn = sqlite3.connect(str(test_db))
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert {"users", "columns", "cards"}.issubset(tables)
