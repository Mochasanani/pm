import json
import logging
import os
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAI, OpenAIError
from pydantic import BaseModel

from app import services
from app.auth import require_user_record
from app.db import db_conn, ensure_default_board

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "openai/gpt-oss-120b"
MAX_HISTORY_TURNS = 20  # user+assistant messages kept per session

logger = logging.getLogger(__name__)

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
    due_date: str | None = None
    position: int | None = None


class ChatResponse(BaseModel):
    response: str
    board_updates: list[BoardUpdate] = []


class ChatRequest(BaseModel):
    message: str
    board_id: int | None = None


# In-memory conversation history keyed by (username, board_id): list of {role, content}
conversations: dict[tuple[str, int], list[dict]] = {}


def build_system_prompt(board: dict) -> str:
    return (
        "You are an assistant for a Kanban board app. You can answer questions "
        "about the board and modify it by returning board_updates. Actions:\n"
        "- create_card: requires column_id and title; optional details, due_date (YYYY-MM-DD)\n"
        "- update_card: requires card_id; optional title, details, due_date (YYYY-MM-DD or null to clear)\n"
        "- delete_card: requires card_id\n"
        "- move_card: requires card_id, column_id, and position (0-indexed)\n"
        "Only include board_updates when the user asks to change the board. "
        "Keep the response field short and conversational.\n"
        f"Current board state: {json.dumps(board)}"
    )


def apply_update(conn, board_id: int, update: BoardUpdate) -> bool:
    """Apply a single update to the given board. Returns True if applied."""
    try:
        if update.action == "create_card":
            if update.column_id is None or update.title is None:
                return False
            services.create_card(
                conn,
                board_id,
                update.column_id,
                update.title,
                update.details or "",
                update.due_date,
            )
        elif update.action == "update_card":
            if update.card_id is None:
                return False
            # Only pass due_date if the model actually set it (presence-aware).
            due = (
                update.due_date
                if "due_date" in update.model_fields_set
                else services.UNSET
            )
            services.update_card(
                conn, board_id, update.card_id, update.title, update.details, due
            )
        elif update.action == "delete_card":
            if update.card_id is None:
                return False
            services.delete_card(conn, board_id, update.card_id)
        elif update.action == "move_card":
            if (
                update.card_id is None
                or update.column_id is None
                or update.position is None
            ):
                return False
            services.move_card(
                conn, board_id, update.card_id, update.column_id, update.position
            )
        else:
            return False
    except services.NotFoundError:
        return False
    return True


@router.post("/chat")
def ai_chat(
    body: ChatRequest,
    user=Depends(require_user_record),
    conn=Depends(db_conn),
):
    username = user["username"]
    if body.board_id is not None:
        target = services.get_user_board(conn, user["id"], body.board_id)
        if not target:
            raise HTTPException(status_code=404, detail="Board not found")
        board_id = body.board_id
    else:
        board_id = ensure_default_board(conn, user["id"])

    board = services.load_board(conn, board_id)
    system_prompt = build_system_prompt(board)

    key = (username, board_id)
    history = conversations.setdefault(key, [])
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

    applied = 0
    skipped = 0
    for update in parsed.board_updates:
        ok = apply_update(conn, board_id, update)
        logger.info(
            "ai_mutation user=%s board=%s action=%s applied=%s payload=%s",
            username, board_id, update.action, ok,
            update.model_dump(exclude_none=True),
        )
        if ok:
            applied += 1
        else:
            skipped += 1

    history.append({"role": "user", "content": body.message})
    history.append({"role": "assistant", "content": parsed.response})
    if len(history) > MAX_HISTORY_TURNS:
        del history[: len(history) - MAX_HISTORY_TURNS]

    return {
        "response": parsed.response,
        "board_updates": [u.model_dump() for u in parsed.board_updates],
        "applied": applied,
        "skipped": skipped,
        "board_id": board_id,
    }


@router.delete("/conversation")
def clear_conversation(
    board_id: int | None = None,
    user=Depends(require_user_record),
):
    username = user["username"]
    if board_id is None:
        # Clear all conversations for the user
        for key in [k for k in conversations if k[0] == username]:
            conversations.pop(key, None)
    else:
        conversations.pop((username, board_id), None)
    return {"ok": True}
