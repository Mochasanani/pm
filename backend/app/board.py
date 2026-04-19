"""Legacy /api/board endpoints: operate on the user's first (default) board.

These remain for backward compatibility with clients/tests that were written
against the single-board MVP. New clients should use /api/boards/{id}/...
"""
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import services
from app.auth import require_user_record
from app.db import db_conn, ensure_default_board, seed_board_columns

router = APIRouter(prefix="/api/board")


@router.get("")
def get_board(user=Depends(require_user_record), conn=Depends(db_conn)):
    board_id = ensure_default_board(conn, user["id"])
    return services.load_board(conn, board_id)


class RenameColumnRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


@router.put("/columns/{column_id}")
def rename_column(
    column_id: int,
    body: RenameColumnRequest,
    user=Depends(require_user_record),
    conn=Depends(db_conn),
):
    board_id = ensure_default_board(conn, user["id"])
    try:
        return services.rename_column(conn, board_id, column_id, body.title)
    except services.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


class CreateCardRequest(BaseModel):
    column_id: int
    title: str = Field(min_length=1, max_length=200)
    details: str = Field(default="", max_length=5000)


@router.post("/cards")
def create_card(
    body: CreateCardRequest,
    user=Depends(require_user_record),
    conn=Depends(db_conn),
):
    board_id = ensure_default_board(conn, user["id"])
    try:
        return services.create_card(
            conn, board_id, body.column_id, body.title, body.details
        )
    except services.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


class UpdateCardRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    details: str | None = Field(default=None, max_length=5000)


@router.put("/cards/{card_id}")
def update_card(
    card_id: int,
    body: UpdateCardRequest,
    user=Depends(require_user_record),
    conn=Depends(db_conn),
):
    board_id = ensure_default_board(conn, user["id"])
    try:
        return services.update_card(conn, board_id, card_id, body.title, body.details)
    except services.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/cards/{card_id}")
def delete_card(
    card_id: int,
    user=Depends(require_user_record),
    conn=Depends(db_conn),
):
    board_id = ensure_default_board(conn, user["id"])
    try:
        services.delete_card(conn, board_id, card_id)
    except services.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"ok": True}


class MoveCardRequest(BaseModel):
    column_id: int
    position: int = Field(ge=0)


@router.put("/cards/{card_id}/move")
def move_card(
    card_id: int,
    body: MoveCardRequest,
    user=Depends(require_user_record),
    conn=Depends(db_conn),
):
    board_id = ensure_default_board(conn, user["id"])
    try:
        services.move_card(conn, board_id, card_id, body.column_id, body.position)
    except services.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"ok": True}


@router.post("/reset")
def reset_board(
    user=Depends(require_user_record),
    conn=Depends(db_conn),
):
    """Wipe and re-seed the default board. Gated by DEV_MODE=1; used by e2e tests."""
    if os.environ.get("DEV_MODE", "").lower() not in ("1", "true", "yes"):
        raise HTTPException(status_code=403, detail="DEV_MODE not enabled")
    board_id = ensure_default_board(conn, user["id"])
    conn.execute(
        "DELETE FROM cards WHERE column_id IN (SELECT id FROM columns WHERE board_id = ?)",
        (board_id,),
    )
    conn.execute("DELETE FROM columns WHERE board_id = ?", (board_id,))
    conn.commit()
    seed_board_columns(conn, board_id, with_cards=True)
    return {"ok": True}
