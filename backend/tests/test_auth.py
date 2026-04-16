def test_login_valid_credentials(client):
    resp = client.post("/api/login", json={"username": "user", "password": "password"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "user"
    assert "session" in resp.cookies


def test_login_invalid_credentials(client):
    resp = client.post("/api/login", json={"username": "user", "password": "wrong"})
    assert resp.status_code == 401
    assert "session" not in resp.cookies


def test_me_authenticated(auth_client):
    resp = auth_client.get("/api/me")
    assert resp.status_code == 200
    assert resp.json()["username"] == "user"


def test_me_unauthenticated(client):
    resp = client.get("/api/me")
    assert resp.status_code == 401


def test_logout_clears_session(auth_client):
    resp = auth_client.post("/api/logout")
    assert resp.status_code == 200
    # Session should be invalidated
    me = auth_client.get("/api/me")
    assert me.status_code == 401
