import os

from fastapi import APIRouter, Cookie, Depends, HTTPException
from pydantic import BaseModel, Field

from app import services
from app.auth import get_current_user
from app.db import db_conn, ensure_user, seed_board

router = APIRouter(prefix="/api/board")


def require_user(session: str | None = Cookie(default=None)) -> str:
    username = get_current_user(session)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return username


@router.get("")
def get_board(username: str = Depends(require_user), conn=Depends(db_conn)):
    user_id = ensure_user(conn, username)
    return services.load_board(conn, user_id)


class RenameColumnRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


@router.put("/columns/{column_id}")
def rename_column(
    column_id: int,
    body: RenameColumnRequest,
    username: str = Depends(require_user),
    conn=Depends(db_conn),
):
    user_id = ensure_user(conn, username)
    try:
        return services.rename_column(conn, user_id, column_id, body.title)
    except services.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


class CreateCardRequest(BaseModel):
    column_id: int
    title: str = Field(min_length=1, max_length=200)
    details: str = Field(default="", max_length=5000)


@router.post("/cards")
def create_card(
    body: CreateCardRequest,
    username: str = Depends(require_user),
    conn=Depends(db_conn),
):
    user_id = ensure_user(conn, username)
    try:
        return services.create_card(conn, user_id, body.column_id, body.title, body.details)
    except services.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


class UpdateCardRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    details: str | None = Field(default=None, max_length=5000)


@router.put("/cards/{card_id}")
def update_card(
    card_id: int,
    body: UpdateCardRequest,
    username: str = Depends(require_user),
    conn=Depends(db_conn),
):
    user_id = ensure_user(conn, username)
    try:
        return services.update_card(conn, user_id, card_id, body.title, body.details)
    except services.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/cards/{card_id}")
def delete_card(
    card_id: int,
    username: str = Depends(require_user),
    conn=Depends(db_conn),
):
    user_id = ensure_user(conn, username)
    try:
        services.delete_card(conn, user_id, card_id)
    except services.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"ok": True}


class MoveCardRequest(BaseModel):
    column_id: int
    position: int = Field(ge=0)


@router.post("/reset")
def reset_board(
    username: str = Depends(require_user),
    conn=Depends(db_conn),
):
    """Wipe and re-seed the board. Gated by DEV_MODE=1 env var; used by e2e tests."""
    if os.environ.get("DEV_MODE", "").lower() not in ("1", "true", "yes"):
        raise HTTPException(status_code=403, detail="DEV_MODE not enabled")
    user_id = ensure_user(conn, username)
    conn.execute(
        "DELETE FROM cards WHERE column_id IN (SELECT id FROM columns WHERE user_id = ?)",
        (user_id,),
    )
    conn.execute("DELETE FROM columns WHERE user_id = ?", (user_id,))
    conn.commit()
    seed_board(conn, user_id)
    return {"ok": True}


@router.put("/cards/{card_id}/move")
def move_card(
    card_id: int,
    body: MoveCardRequest,
    username: str = Depends(require_user),
    conn=Depends(db_conn),
):
    user_id = ensure_user(conn, username)
    try:
        services.move_card(conn, user_id, card_id, body.column_id, body.position)
    except services.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"ok": True}
