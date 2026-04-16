import secrets
from fastapi import APIRouter, Cookie, Response
from pydantic import BaseModel

from app.db import get_connection, ensure_user, seed_board

router = APIRouter(prefix="/api")

VALID_USERNAME = "user"
VALID_PASSWORD = "password"

# In-memory session store: token -> username
sessions: dict[str, str] = {}


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginRequest, response: Response):
    if body.username != VALID_USERNAME or body.password != VALID_PASSWORD:
        response.status_code = 401
        return {"error": "Invalid credentials"}

    conn = get_connection()
    user_id = ensure_user(conn, body.username)
    seed_board(conn, user_id)
    conn.close()

    token = secrets.token_urlsafe(32)
    sessions[token] = body.username
    response.set_cookie(key="session", value=token, httponly=True, samesite="lax")
    return {"username": body.username}


@router.post("/logout")
def logout(response: Response, session: str | None = Cookie(default=None)):
    if session and session in sessions:
        del sessions[session]
    response.delete_cookie(key="session")
    return {"ok": True}


@router.get("/me")
def me(session: str | None = Cookie(default=None)):
    if not session or session not in sessions:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})
    return {"username": sessions[session]}


def get_current_user(session: str | None = Cookie(default=None)) -> str | None:
    """Return username if session is valid, else None."""
    if not session or session not in sessions:
        return None
    return sessions[session]
