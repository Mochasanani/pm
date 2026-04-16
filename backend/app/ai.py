import json
import os
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAI, OpenAIError
from pydantic import BaseModel

from app.board import get_board, require_user
from app.db import ensure_user, get_connection

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "openai/gpt-oss-120b"

router = APIRouter(prefix="/api/ai")


def get_client() -> OpenAI:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not set")
    return OpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL)


def ask(prompt: str) -> str:
    client = get_client()
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
    except OpenAIError as exc:
        raise HTTPException(status_code=502, detail=f"OpenRouter error: {exc}")
    return completion.choices[0].message.content or ""


@router.post("/test")
def ai_test():
    answer = ask("What is 2+2? Respond with just the number.")
    return {"answer": answer}


class BoardUpdate(BaseModel):
    action: Literal["create_card", "update_card", "delete_card", "move_card"]
    card_id: int | None = None
    column_id: int | None = None
    title: str | None = None
    details: str | None = None
    position: int | None = None


class ChatResponse(BaseModel):
    response: str
    board_updates: list[BoardUpdate] = []


class ChatRequest(BaseModel):
    message: str


# In-memory conversation history per username: list of {role, content}
conversations: dict[str, list[dict]] = {}


def build_system_prompt(board: dict) -> str:
    return (
        "You are an assistant for a Kanban board app. You can answer questions "
        "about the board and modify it by returning board_updates. Actions:\n"
        "- create_card: requires column_id and title; optional details\n"
        "- update_card: requires card_id; optional title and/or details\n"
        "- delete_card: requires card_id\n"
        "- move_card: requires card_id, column_id, and position (0-indexed)\n"
        "Only include board_updates when the user asks to change the board. "
        "Keep the response field short and conversational.\n"
        f"Current board state: {json.dumps(board)}"
    )


def apply_update(conn, user_id: int, update: BoardUpdate) -> None:
    if update.action == "create_card":
        if update.column_id is None or update.title is None:
            return
        col = conn.execute(
            "SELECT id FROM columns WHERE id = ? AND user_id = ?",
            (update.column_id, user_id),
        ).fetchone()
        if not col:
            return
        max_pos = conn.execute(
            "SELECT COALESCE(MAX(position), -1) AS mp FROM cards WHERE column_id = ?",
            (update.column_id,),
        ).fetchone()["mp"]
        conn.execute(
            "INSERT INTO cards (column_id, title, details, position) VALUES (?, ?, ?, ?)",
            (update.column_id, update.title, update.details or "No details yet.", max_pos + 1),
        )
    elif update.action == "update_card":
        if update.card_id is None:
            return
        card = conn.execute(
            """SELECT cards.id FROM cards
               JOIN columns ON cards.column_id = columns.id
               WHERE cards.id = ? AND columns.user_id = ?""",
            (update.card_id, user_id),
        ).fetchone()
        if not card:
            return
        sets, params = [], []
        if update.title is not None:
            sets.append("title = ?")
            params.append(update.title)
        if update.details is not None:
            sets.append("details = ?")
            params.append(update.details)
        if sets:
            params.append(update.card_id)
            conn.execute(f"UPDATE cards SET {', '.join(sets)} WHERE id = ?", params)
    elif update.action == "delete_card":
        if update.card_id is None:
            return
        card = conn.execute(
            """SELECT cards.id, cards.column_id, cards.position FROM cards
               JOIN columns ON cards.column_id = columns.id
               WHERE cards.id = ? AND columns.user_id = ?""",
            (update.card_id, user_id),
        ).fetchone()
        if not card:
            return
        conn.execute("DELETE FROM cards WHERE id = ?", (update.card_id,))
        conn.execute(
            "UPDATE cards SET position = position - 1 WHERE column_id = ? AND position > ?",
            (card["column_id"], card["position"]),
        )
    elif update.action == "move_card":
        if update.card_id is None or update.column_id is None or update.position is None:
            return
        card = conn.execute(
            """SELECT cards.id, cards.column_id, cards.position FROM cards
               JOIN columns ON cards.column_id = columns.id
               WHERE cards.id = ? AND columns.user_id = ?""",
            (update.card_id, user_id),
        ).fetchone()
        target = conn.execute(
            "SELECT id FROM columns WHERE id = ? AND user_id = ?",
            (update.column_id, user_id),
        ).fetchone()
        if not card or not target:
            return
        conn.execute(
            "UPDATE cards SET position = position - 1 WHERE column_id = ? AND position > ?",
            (card["column_id"], card["position"]),
        )
        conn.execute(
            "UPDATE cards SET position = position + 1 WHERE column_id = ? AND position >= ?",
            (update.column_id, update.position),
        )
        conn.execute(
            "UPDATE cards SET column_id = ?, position = ? WHERE id = ?",
            (update.column_id, update.position, update.card_id),
        )
    conn.commit()


@router.post("/chat")
def ai_chat(body: ChatRequest, username: str = Depends(require_user)):
    board = get_board(username=username)
    system_prompt = build_system_prompt(board)

    history = conversations.setdefault(username, [])
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": body.message})

    client = get_client()
    try:
        completion = client.chat.completions.parse(
            model=MODEL,
            messages=messages,
            response_format=ChatResponse,
        )
    except OpenAIError as exc:
        raise HTTPException(status_code=502, detail=f"OpenRouter error: {exc}")

    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise HTTPException(status_code=502, detail="AI returned malformed response")

    conn = get_connection()
    user_id = ensure_user(conn, username)
    for update in parsed.board_updates:
        apply_update(conn, user_id, update)
    conn.close()

    history.append({"role": "user", "content": body.message})
    history.append({"role": "assistant", "content": parsed.response})

    return {
        "response": parsed.response,
        "board_updates": [u.model_dump() for u in parsed.board_updates],
    }
