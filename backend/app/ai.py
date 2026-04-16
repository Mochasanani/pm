import json
import logging
import os
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAI, OpenAIError
from pydantic import BaseModel

from app import services
from app.board import require_user
from app.db import db_conn, ensure_user

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


def apply_update(conn, user_id: int, update: BoardUpdate) -> bool:
    """Apply a single update. Returns True if applied, False if skipped."""
    try:
        if update.action == "create_card":
            if update.column_id is None or update.title is None:
                return False
            services.create_card(
                conn, user_id, update.column_id, update.title, update.details or ""
            )
        elif update.action == "update_card":
            if update.card_id is None:
                return False
            services.update_card(
                conn, user_id, update.card_id, update.title, update.details
            )
        elif update.action == "delete_card":
            if update.card_id is None:
                return False
            services.delete_card(conn, user_id, update.card_id)
        elif update.action == "move_card":
            if (
                update.card_id is None
                or update.column_id is None
                or update.position is None
            ):
                return False
            services.move_card(
                conn, user_id, update.card_id, update.column_id, update.position
            )
        else:
            return False
    except services.NotFoundError:
        return False
    return True


@router.post("/chat")
def ai_chat(
    body: ChatRequest,
    username: str = Depends(require_user),
    conn=Depends(db_conn),
):
    user_id = ensure_user(conn, username)
    board = services.load_board(conn, user_id)
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

    applied = 0
    skipped = 0
    for update in parsed.board_updates:
        ok = apply_update(conn, user_id, update)
        logger.info(
            "ai_mutation user=%s action=%s applied=%s payload=%s",
            username, update.action, ok, update.model_dump(exclude_none=True),
        )
        if ok:
            applied += 1
        else:
            skipped += 1

    history.append({"role": "user", "content": body.message})
    history.append({"role": "assistant", "content": parsed.response})
    # Keep only the most recent MAX_HISTORY_TURNS messages
    if len(history) > MAX_HISTORY_TURNS:
        del history[: len(history) - MAX_HISTORY_TURNS]

    return {
        "response": parsed.response,
        "board_updates": [u.model_dump() for u in parsed.board_updates],
        "applied": applied,
        "skipped": skipped,
    }


@router.delete("/conversation")
def clear_conversation(username: str = Depends(require_user)):
    conversations.pop(username, None)
    return {"ok": True}
