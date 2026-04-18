import sqlite3
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.db import init_db, ensure_default_board
from app.users import ensure_default_user
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
    user_id = ensure_default_user(conn)
    ensure_default_board(conn, user_id)
    conn.close()
    with patch("app.db.DB_PATH", db_path):
        yield db_path


@pytest.fixture()
def client():
    from app.main import app
    return TestClient(app)


@pytest.fixture()
def auth_client(client):
    """A test client that is already logged in as the default user."""
    resp = client.post("/api/login", json={"username": "user", "password": "password"})
    assert resp.status_code == 200
    client.cookies.set("session", resp.cookies["session"])
    return client


@pytest.fixture()
def register_and_login(client):
    """Factory to register and log in a fresh user. Returns a logged-in TestClient."""
    def _make(username: str = "alice", password: str = "secretpass", **extra):
        resp = client.post(
            "/api/register",
            json={"username": username, "password": password, **extra},
        )
        assert resp.status_code == 201, resp.text
        client.cookies.set("session", resp.cookies["session"])
        return client, resp.json()

    return _make
