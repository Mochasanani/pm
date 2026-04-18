"""Multi-board API: /api/boards and board-scoped column/card endpoints."""
import re
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app import services
from app.auth import require_user_record
from app.db import db_conn, ensure_default_board

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def _validate_color(value: str) -> str:
    if not _HEX_COLOR.match(value):
        raise ValueError("color must be a #RRGGBB hex string")
    return value.lower()


def _validate_due_date(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    if not _ISO_DATE.match(value):
        raise ValueError("due_date must be YYYY-MM-DD")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("due_date must be a valid calendar date") from exc
    return value

router = APIRouter(prefix="/api/boards")


def _require_board(conn, user_id: int, board_id: int) -> dict:
    board = services.get_user_board(conn, user_id, board_id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    return board


# ---------------- Boards CRUD ----------------

class CreateBoardRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)


class UpdateBoardRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)


@router.get("")
def list_boards(user=Depends(require_user_record), conn=Depends(db_conn)):
    ensure_default_board(conn, user["id"])
    return services.list_user_boards(conn, user["id"])


@router.post("", status_code=201)
def create_board(
    body: CreateBoardRequest,
    user=Depends(require_user_record),
    conn=Depends(db_conn),
):
    return services.create_board(conn, user["id"], body.name, body.description)


@router.get("/{board_id}")
def get_board(
    board_id: int, user=Depends(require_user_record), conn=Depends(db_conn)
):
    board = _require_board(conn, user["id"], board_id)
    content = services.load_board(conn, board_id)
    return {"board": board, **content}


@router.put("/{board_id}")
def rename_board(
    board_id: int,
    body: UpdateBoardRequest,
    user=Depends(require_user_record),
    conn=Depends(db_conn),
):
    _require_board(conn, user["id"], board_id)
    try:
        return services.update_board(
            conn, user["id"], board_id, body.name, body.description
        )
    except services.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/{board_id}")
def delete_board(
    board_id: int, user=Depends(require_user_record), conn=Depends(db_conn)
):
    try:
        services.delete_board(conn, user["id"], board_id)
    except services.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"ok": True}


# ---------------- Column & card operations (scoped to board) ----------------

class RenameColumnRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


@router.put("/{board_id}/columns/{column_id}")
def rename_column(
    board_id: int,
    column_id: int,
    body: RenameColumnRequest,
    user=Depends(require_user_record),
    conn=Depends(db_conn),
):
    _require_board(conn, user["id"], board_id)
    try:
        return services.rename_column(conn, board_id, column_id, body.title)
    except services.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


class CreateCardRequest(BaseModel):
    column_id: int
    title: str = Field(min_length=1, max_length=200)
    details: str = Field(default="", max_length=5000)
    due_date: str | None = None

    @field_validator("due_date")
    @classmethod
    def _check_due_date(cls, v: str | None) -> str | None:
        return _validate_due_date(v)


@router.post("/{board_id}/cards")
def create_card(
    body: CreateCardRequest,
    board_id: int,
    user=Depends(require_user_record),
    conn=Depends(db_conn),
):
    _require_board(conn, user["id"], board_id)
    try:
        return services.create_card(
            conn,
            board_id,
            body.column_id,
            body.title,
            body.details,
            body.due_date,
        )
    except services.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


class UpdateCardRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    details: str | None = Field(default=None, max_length=5000)
    # Use a dict/exclude_unset pattern via model_fields_set to detect presence.
    due_date: str | None = None

    @field_validator("due_date")
    @classmethod
    def _check_due_date(cls, v: str | None) -> str | None:
        return _validate_due_date(v)


@router.put("/{board_id}/cards/{card_id}")
def update_card(
    body: UpdateCardRequest,
    board_id: int,
    card_id: int,
    user=Depends(require_user_record),
    conn=Depends(db_conn),
):
    _require_board(conn, user["id"], board_id)
    # Distinguish "due_date not sent" from "due_date: null".
    due = body.due_date if "due_date" in body.model_fields_set else services.UNSET
    try:
        return services.update_card(
            conn, board_id, card_id, body.title, body.details, due
        )
    except services.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/{board_id}/cards/{card_id}")
def delete_card(
    board_id: int,
    card_id: int,
    user=Depends(require_user_record),
    conn=Depends(db_conn),
):
    _require_board(conn, user["id"], board_id)
    try:
        services.delete_card(conn, board_id, card_id)
    except services.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"ok": True}


class MoveCardRequest(BaseModel):
    column_id: int
    position: int = Field(ge=0)


@router.put("/{board_id}/cards/{card_id}/move")
def move_card(
    board_id: int,
    card_id: int,
    body: MoveCardRequest,
    user=Depends(require_user_record),
    conn=Depends(db_conn),
):
    _require_board(conn, user["id"], board_id)
    try:
        services.move_card(
            conn, board_id, card_id, body.column_id, body.position
        )
    except services.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"ok": True}


# ---------------- Labels ----------------

class CreateLabelRequest(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    color: str = Field(default="#888888")

    @field_validator("color")
    @classmethod
    def _check_color(cls, v: str) -> str:
        return _validate_color(v)


class UpdateLabelRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    color: str | None = None

    @field_validator("color")
    @classmethod
    def _check_color(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _validate_color(v)


class SetCardLabelsRequest(BaseModel):
    label_ids: list[int] = Field(default_factory=list)


@router.get("/{board_id}/labels")
def list_labels(
    board_id: int, user=Depends(require_user_record), conn=Depends(db_conn)
):
    _require_board(conn, user["id"], board_id)
    return services.list_labels(conn, board_id)


@router.post("/{board_id}/labels", status_code=201)
def create_label(
    board_id: int,
    body: CreateLabelRequest,
    user=Depends(require_user_record),
    conn=Depends(db_conn),
):
    _require_board(conn, user["id"], board_id)
    return services.create_label(conn, board_id, body.name, body.color)


@router.put("/{board_id}/labels/{label_id}")
def update_label(
    board_id: int,
    label_id: int,
    body: UpdateLabelRequest,
    user=Depends(require_user_record),
    conn=Depends(db_conn),
):
    _require_board(conn, user["id"], board_id)
    try:
        return services.update_label(
            conn, board_id, label_id, body.name, body.color
        )
    except services.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/{board_id}/labels/{label_id}")
def delete_label(
    board_id: int,
    label_id: int,
    user=Depends(require_user_record),
    conn=Depends(db_conn),
):
    _require_board(conn, user["id"], board_id)
    try:
        services.delete_label(conn, board_id, label_id)
    except services.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"ok": True}


@router.put("/{board_id}/cards/{card_id}/labels")
def set_card_labels(
    board_id: int,
    card_id: int,
    body: SetCardLabelsRequest,
    user=Depends(require_user_record),
    conn=Depends(db_conn),
):
    _require_board(conn, user["id"], board_id)
    try:
        label_ids = services.set_card_labels(
            conn, board_id, card_id, body.label_ids
        )
    except services.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"card_id": card_id, "label_ids": label_ids}
