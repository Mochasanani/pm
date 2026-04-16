from fastapi.testclient import TestClient

from app.main import app
from app.auth import sessions

client = TestClient(app)


def setup_function():
    sessions.clear()


def test_login_valid_credentials():
    resp = client.post("/api/login", json={"username": "user", "password": "password"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "user"
    assert "session" in resp.cookies


def test_login_invalid_credentials():
    resp = client.post("/api/login", json={"username": "user", "password": "wrong"})
    assert resp.status_code == 401
    assert "session" not in resp.cookies


def test_me_authenticated():
    login = client.post("/api/login", json={"username": "user", "password": "password"})
    resp = client.get("/api/me", cookies=login.cookies)
    assert resp.status_code == 200
    assert resp.json()["username"] == "user"


def test_me_unauthenticated():
    resp = client.get("/api/me")
    assert resp.status_code == 401


def test_logout_clears_session():
    login = client.post("/api/login", json={"username": "user", "password": "password"})
    resp = client.post("/api/logout", cookies=login.cookies)
    assert resp.status_code == 200
    # Session should be invalidated
    me = client.get("/api/me", cookies=login.cookies)
    assert me.status_code == 401
