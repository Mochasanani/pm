"""Authentication: login, logout, session, and registration."""
import os
import secrets

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field

from app import users
from app.db import db_conn, ensure_default_board, get_connection

router = APIRouter(prefix="/api")

# In-memory session store: token -> username
sessions: dict[str, str] = {}


def _cookie_secure() -> bool:
    return os.environ.get("COOKIE_SECURE", "").lower() in ("1", "true", "yes")


def _invalidate_user_sessions(username: str) -> None:
    for token in [t for t, u in sessions.items() if u == username]:
        del sessions[token]


def _set_session_cookie(response: Response, username: str) -> str:
    token = secrets.token_urlsafe(32)
    sessions[token] = username
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(),
    )
    return token


def _user_payload(user: dict) -> dict:
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user.get("email"),
        "display_name": user.get("display_name") or user["username"],
    }


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginRequest, response: Response):
    conn = get_connection()
    try:
        user = users.get_user_by_username(conn, body.username)
        if not user or not users.verify_password(body.password, user["password_hash"]):
            return JSONResponse(status_code=401, content={"error": "Invalid credentials"})
        ensure_default_board(conn, user["id"])
    finally:
        conn.close()

    _invalidate_user_sessions(body.username)
    _set_session_cookie(response, body.username)
    return _user_payload(user)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=40, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=200)
    email: EmailStr | None = None
    display_name: str | None = Field(default=None, max_length=100)


@router.post("/register", status_code=201)
def register(body: RegisterRequest, response: Response):
    conn = get_connection()
    try:
        try:
            user = users.create_user(
                conn,
                username=body.username,
                password=body.password,
                email=body.email,
                display_name=body.display_name,
            )
        except ValueError as exc:
            return JSONResponse(status_code=409, content={"error": str(exc)})
        ensure_default_board(conn, user["id"])
    finally:
        conn.close()

    _set_session_cookie(response, body.username)
    return _user_payload(user)


@router.post("/logout")
def logout(response: Response, session: str | None = Cookie(default=None)):
    if session and session in sessions:
        del sessions[session]
    response.delete_cookie(key="session")
    return {"ok": True}


@router.get("/me")
def me(session: str | None = Cookie(default=None)):
    if not session or session not in sessions:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})
    conn = get_connection()
    try:
        user = users.get_user_by_username(conn, sessions[session])
    finally:
        conn.close()
    if not user:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})
    return _user_payload(user)


class UpdateMeRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=200)


@router.put("/me")
def update_me(
    body: UpdateMeRequest,
    session: str | None = Cookie(default=None),
    conn=Depends(db_conn),
):
    if not session or session not in sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = users.get_user_by_username(conn, sessions[session])
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        updated = users.update_user(
            conn,
            user["id"],
            display_name=body.display_name,
            email=body.email,
            password=body.password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return _user_payload(updated)


def get_current_user(session: str | None = Cookie(default=None)) -> str | None:
    """Return username if session is valid, else None."""
    if not session or session not in sessions:
        return None
    return sessions[session]


def require_user(session: str | None = Cookie(default=None)) -> str:
    username = get_current_user(session)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return username


def require_user_record(
    session: str | None = Cookie(default=None), conn=Depends(db_conn)
) -> dict:
    """Require an authenticated user and return their full user row."""
    username = get_current_user(session)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = users.get_user_by_username(conn, username)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
