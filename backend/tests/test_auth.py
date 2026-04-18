def test_login_valid_credentials(client):
    resp = client.post("/api/login", json={"username": "user", "password": "password"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "user"
    assert body["display_name"]
    assert "session" in resp.cookies


def test_login_invalid_credentials(client):
    resp = client.post("/api/login", json={"username": "user", "password": "wrong"})
    assert resp.status_code == 401
    assert "session" not in resp.cookies


def test_login_unknown_user(client):
    resp = client.post("/api/login", json={"username": "ghost", "password": "whatever"})
    assert resp.status_code == 401


def test_me_authenticated(auth_client):
    resp = auth_client.get("/api/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "user"
    assert "display_name" in body


def test_me_unauthenticated(client):
    resp = client.get("/api/me")
    assert resp.status_code == 401


def test_me_session_for_deleted_user(auth_client):
    """If the backing user disappears, /me should 401 instead of 500."""
    from app.db import get_connection

    conn = get_connection()
    conn.execute("DELETE FROM users WHERE username = 'user'")
    conn.commit()
    conn.close()

    resp = auth_client.get("/api/me")
    assert resp.status_code == 401


def test_logout_clears_session(auth_client):
    resp = auth_client.post("/api/logout")
    assert resp.status_code == 200
    me = auth_client.get("/api/me")
    assert me.status_code == 401


def test_relogin_invalidates_prior_session(client):
    first = client.post("/api/login", json={"username": "user", "password": "password"})
    assert first.status_code == 200
    first_token = first.cookies["session"]

    second_client = client
    second_client.cookies.clear()
    second = second_client.post("/api/login", json={"username": "user", "password": "password"})
    assert second.status_code == 200
    second_token = second.cookies["session"]
    assert first_token != second_token

    from app.auth import sessions
    assert first_token not in sessions
    assert second_token in sessions


# ---------- Registration ----------

def test_register_creates_user_and_logs_in(client):
    resp = client.post(
        "/api/register",
        json={
            "username": "alice",
            "password": "secretpass",
            "email": "alice@example.com",
            "display_name": "Alice A.",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "alice"
    assert body["email"] == "alice@example.com"
    assert body["display_name"] == "Alice A."
    assert "session" in resp.cookies

    me = client.get("/api/me")
    assert me.status_code == 200
    assert me.json()["username"] == "alice"


def test_register_without_email_or_display(client):
    resp = client.post(
        "/api/register", json={"username": "bob123", "password": "secretpass"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] is None
    assert body["display_name"] == "bob123"


def test_register_conflict_on_duplicate_username(client):
    client.post("/api/register", json={"username": "alice", "password": "secretpass"})
    client.cookies.clear()
    resp = client.post(
        "/api/register", json={"username": "alice", "password": "anotherpass"}
    )
    assert resp.status_code == 409


def test_register_conflict_on_duplicate_email(client):
    client.post(
        "/api/register",
        json={"username": "alice", "password": "secretpass", "email": "a@b.com"},
    )
    client.cookies.clear()
    resp = client.post(
        "/api/register",
        json={"username": "bob", "password": "secretpass", "email": "a@b.com"},
    )
    assert resp.status_code == 409


def test_register_validates_short_password(client):
    resp = client.post(
        "/api/register", json={"username": "alice", "password": "short"}
    )
    assert resp.status_code == 422


def test_register_validates_bad_username(client):
    resp = client.post(
        "/api/register", json={"username": "a b!", "password": "secretpass"}
    )
    assert resp.status_code == 422


def test_register_validates_bad_email(client):
    resp = client.post(
        "/api/register",
        json={
            "username": "alice",
            "password": "secretpass",
            "email": "not-an-email",
        },
    )
    assert resp.status_code == 422


def test_register_seeds_default_board(register_and_login):
    client, _ = register_and_login("charlie", "secretpass")
    boards = client.get("/api/boards").json()
    assert len(boards) == 1
    assert boards[0]["name"]


def test_new_users_boards_are_isolated(client):
    # Register alice
    alice = client.post(
        "/api/register", json={"username": "alice", "password": "secretpass"}
    )
    assert alice.status_code == 201
    alice_token = client.cookies["session"]

    alice_boards = client.get("/api/boards").json()
    assert len(alice_boards) == 1

    # Create a second board as alice
    created = client.post(
        "/api/boards", json={"name": "Alice secrets"}
    ).json()
    alice_board_id = created["id"]

    # Now log in as default user
    client.cookies.clear()
    client.post("/api/login", json={"username": "user", "password": "password"})

    user_boards = client.get("/api/boards").json()
    user_board_ids = [b["id"] for b in user_boards]
    assert alice_board_id not in user_board_ids

    # The default user can't access alice's board
    r = client.get(f"/api/boards/{alice_board_id}")
    assert r.status_code == 404

    # Restore alice for sanity
    assert alice_token  # referenced to silence lints


# ---------- Profile update ----------

def test_update_me_changes_display_name(auth_client):
    resp = auth_client.put("/api/me", json={"display_name": "New Name"})
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "New Name"


def test_update_me_password_changes_login(auth_client, client):
    resp = auth_client.put("/api/me", json={"password": "brandnewpass"})
    assert resp.status_code == 200

    client.cookies.clear()
    bad = client.post("/api/login", json={"username": "user", "password": "password"})
    assert bad.status_code == 401
    good = client.post("/api/login", json={"username": "user", "password": "brandnewpass"})
    assert good.status_code == 200


def test_update_me_requires_auth(client):
    resp = client.put("/api/me", json={"display_name": "x"})
    assert resp.status_code == 401


def test_update_me_email_conflict(client):
    # Register bob with an email
    client.post(
        "/api/register",
        json={"username": "bob", "password": "secretpass", "email": "bob@x.com"},
    )
    # Log in as the default user
    client.cookies.clear()
    login = client.post("/api/login", json={"username": "user", "password": "password"})
    assert login.status_code == 200
    client.cookies.set("session", login.cookies["session"])

    # Try to steal bob's email as the default user
    resp = client.put("/api/me", json={"email": "bob@x.com"})
    assert resp.status_code == 409
