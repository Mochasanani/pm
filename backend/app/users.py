"""User persistence and password hashing."""
import sqlite3

import bcrypt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def get_user_by_username(conn: sqlite3.Connection, username: str) -> dict | None:
    row = conn.execute(
        "SELECT id, username, email, password_hash, display_name FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    return dict(row) if row else None


def get_user_by_id(conn: sqlite3.Connection, user_id: int) -> dict | None:
    row = conn.execute(
        "SELECT id, username, email, password_hash, display_name FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    return dict(row) if row else None


def create_user(
    conn: sqlite3.Connection,
    username: str,
    password: str,
    email: str | None = None,
    display_name: str | None = None,
) -> dict:
    if get_user_by_username(conn, username):
        raise ValueError("Username already taken")
    if email:
        exists = conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
        if exists:
            raise ValueError("Email already registered")

    cur = conn.execute(
        "INSERT INTO users (username, email, password_hash, display_name) VALUES (?, ?, ?, ?)",
        (username, email, hash_password(password), display_name or username),
    )
    conn.commit()
    user_id = cur.lastrowid
    assert user_id is not None
    created = get_user_by_id(conn, user_id)
    assert created is not None
    return created


def update_user(
    conn: sqlite3.Connection,
    user_id: int,
    display_name: str | None = None,
    email: str | None = None,
    password: str | None = None,
) -> dict:
    user = get_user_by_id(conn, user_id)
    if not user:
        raise ValueError("User not found")

    sets: list[str] = []
    params: list = []
    if display_name is not None:
        sets.append("display_name = ?")
        params.append(display_name)
    if email is not None:
        existing = conn.execute(
            "SELECT 1 FROM users WHERE email = ? AND id != ?", (email, user_id)
        ).fetchone()
        if existing:
            raise ValueError("Email already registered")
        sets.append("email = ?")
        params.append(email)
    if password is not None:
        sets.append("password_hash = ?")
        params.append(hash_password(password))

    if sets:
        params.append(user_id)
        conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE id = ?", params)
        conn.commit()

    updated = get_user_by_id(conn, user_id)
    assert updated is not None
    return updated


def ensure_default_user(conn: sqlite3.Connection) -> int:
    """Ensure the demo 'user' account exists. Returns its id."""
    existing = get_user_by_username(conn, "user")
    if existing:
        return existing["id"]
    created = create_user(
        conn, username="user", password="password", display_name="Demo User"
    )
    return created["id"]
