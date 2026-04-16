from fastapi import APIRouter, Cookie, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.auth import get_current_user
from app.db import get_connection, ensure_user

router = APIRouter(prefix="/api/board")


def require_user(session: str | None = Cookie(default=None)) -> str:
    username = get_current_user(session)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return username


@router.get("")
def get_board(username: str = Depends(require_user)):
    conn = get_connection()
    user_id = ensure_user(conn, username)

    columns = conn.execute(
        "SELECT id, title, position FROM columns WHERE user_id = ? ORDER BY position",
        (user_id,),
    ).fetchall()

    result_columns = []
    all_cards: dict[int, dict] = {}

    for col in columns:
        cards = conn.execute(
            "SELECT id, title, details, position FROM cards WHERE column_id = ? ORDER BY position",
            (col["id"],),
        ).fetchall()
        card_ids = []
        for card in cards:
            card_dict = {"id": card["id"], "title": card["title"], "details": card["details"]}
            all_cards[card["id"]] = card_dict
            card_ids.append(card["id"])
        result_columns.append({
            "id": col["id"],
            "title": col["title"],
            "cardIds": card_ids,
        })

    conn.close()
    return {"columns": result_columns, "cards": all_cards}


class RenameColumnRequest(BaseModel):
    title: str


@router.put("/columns/{column_id}")
def rename_column(column_id: int, body: RenameColumnRequest, username: str = Depends(require_user)):
    conn = get_connection()
    user_id = ensure_user(conn, username)

    col = conn.execute(
        "SELECT id FROM columns WHERE id = ? AND user_id = ?", (column_id, user_id)
    ).fetchone()
    if not col:
        conn.close()
        return JSONResponse(status_code=404, content={"error": "Column not found"})

    conn.execute("UPDATE columns SET title = ? WHERE id = ?", (body.title, column_id))
    conn.commit()
    conn.close()
    return {"id": column_id, "title": body.title}


class CreateCardRequest(BaseModel):
    column_id: int
    title: str
    details: str = ""


@router.post("/cards")
def create_card(body: CreateCardRequest, username: str = Depends(require_user)):
    conn = get_connection()
    user_id = ensure_user(conn, username)

    col = conn.execute(
        "SELECT id FROM columns WHERE id = ? AND user_id = ?", (body.column_id, user_id)
    ).fetchone()
    if not col:
        conn.close()
        return JSONResponse(status_code=404, content={"error": "Column not found"})

    max_pos = conn.execute(
        "SELECT COALESCE(MAX(position), -1) as mp FROM cards WHERE column_id = ?", (body.column_id,)
    ).fetchone()["mp"]

    cur = conn.execute(
        "INSERT INTO cards (column_id, title, details, position) VALUES (?, ?, ?, ?)",
        (body.column_id, body.title, body.details or "No details yet.", max_pos + 1),
    )
    conn.commit()
    card_id = cur.lastrowid
    conn.close()
    return {"id": card_id, "title": body.title, "details": body.details or "No details yet."}


class UpdateCardRequest(BaseModel):
    title: str | None = None
    details: str | None = None


@router.put("/cards/{card_id}")
def update_card(card_id: int, body: UpdateCardRequest, username: str = Depends(require_user)):
    conn = get_connection()
    user_id = ensure_user(conn, username)

    card = conn.execute(
        """SELECT cards.id FROM cards
           JOIN columns ON cards.column_id = columns.id
           WHERE cards.id = ? AND columns.user_id = ?""",
        (card_id, user_id),
    ).fetchone()
    if not card:
        conn.close()
        return JSONResponse(status_code=404, content={"error": "Card not found"})

    updates = []
    params: list = []
    if body.title is not None:
        updates.append("title = ?")
        params.append(body.title)
    if body.details is not None:
        updates.append("details = ?")
        params.append(body.details)

    if updates:
        params.append(card_id)
        conn.execute(f"UPDATE cards SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()

    row = conn.execute("SELECT id, title, details FROM cards WHERE id = ?", (card_id,)).fetchone()
    conn.close()
    return {"id": row["id"], "title": row["title"], "details": row["details"]}


@router.delete("/cards/{card_id}")
def delete_card(card_id: int, username: str = Depends(require_user)):
    conn = get_connection()
    user_id = ensure_user(conn, username)

    card = conn.execute(
        """SELECT cards.id, cards.column_id, cards.position FROM cards
           JOIN columns ON cards.column_id = columns.id
           WHERE cards.id = ? AND columns.user_id = ?""",
        (card_id, user_id),
    ).fetchone()
    if not card:
        conn.close()
        return JSONResponse(status_code=404, content={"error": "Card not found"})

    conn.execute("DELETE FROM cards WHERE id = ?", (card_id,))
    # Renumber positions in the column
    conn.execute(
        """UPDATE cards SET position = position - 1
           WHERE column_id = ? AND position > ?""",
        (card["column_id"], card["position"]),
    )
    conn.commit()
    conn.close()
    return {"ok": True}


class MoveCardRequest(BaseModel):
    column_id: int
    position: int


@router.put("/cards/{card_id}/move")
def move_card(card_id: int, body: MoveCardRequest, username: str = Depends(require_user)):
    conn = get_connection()
    user_id = ensure_user(conn, username)

    card = conn.execute(
        """SELECT cards.id, cards.column_id, cards.position FROM cards
           JOIN columns ON cards.column_id = columns.id
           WHERE cards.id = ? AND columns.user_id = ?""",
        (card_id, user_id),
    ).fetchone()
    if not card:
        conn.close()
        return JSONResponse(status_code=404, content={"error": "Card not found"})

    target_col = conn.execute(
        "SELECT id FROM columns WHERE id = ? AND user_id = ?", (body.column_id, user_id)
    ).fetchone()
    if not target_col:
        conn.close()
        return JSONResponse(status_code=404, content={"error": "Target column not found"})

    old_col_id = card["column_id"]
    old_pos = card["position"]

    # Remove from old position
    conn.execute(
        "UPDATE cards SET position = position - 1 WHERE column_id = ? AND position > ?",
        (old_col_id, old_pos),
    )

    # Make room in target column
    conn.execute(
        "UPDATE cards SET position = position + 1 WHERE column_id = ? AND position >= ?",
        (body.column_id, body.position),
    )

    # Move the card
    conn.execute(
        "UPDATE cards SET column_id = ?, position = ? WHERE id = ?",
        (body.column_id, body.position, card_id),
    )

    conn.commit()
    conn.close()
    return {"ok": True}
