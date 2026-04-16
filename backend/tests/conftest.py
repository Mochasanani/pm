import sqlite3
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.db import init_db
from app.auth import sessions
from app.ai import conversations


@pytest.fixture(autouse=True)
def clean_sessions():
    sessions.clear()
    conversations.clear()
    yield
    sessions.clear()
    conversations.clear()


@pytest.fixture(autouse=True)
def test_db(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    init_db(conn)
    conn.close()
    with patch("app.db.DB_PATH", db_path):
        yield db_path


@pytest.fixture()
def client():
    from app.main import app
    return TestClient(app)


@pytest.fixture()
def auth_client(client):
    """A test client that is already logged in."""
    resp = client.post("/api/login", json={"username": "user", "password": "password"})
    assert resp.status_code == 200
    client.cookies.set("session", resp.cookies["session"])
    return client
