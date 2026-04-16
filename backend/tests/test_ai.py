import os
from unittest.mock import MagicMock, patch

import pytest
from openai import APIError

from app import ai
from app.ai import BoardUpdate, ChatResponse, apply_update, build_system_prompt
from app.db import ensure_user, get_connection


def _mock_completion(content: str):
    completion = MagicMock()
    completion.choices = [MagicMock(message=MagicMock(content=content))]
    return completion


@pytest.fixture
def fake_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")


def test_get_client_uses_openrouter_base(fake_key):
    client = ai.get_client()
    assert str(client.base_url).startswith(ai.OPENROUTER_BASE_URL)


def test_get_client_missing_key_raises(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(Exception) as exc:
        ai.get_client()
    assert "OPENROUTER_API_KEY" in str(exc.value.detail)


def test_ai_test_endpoint_returns_answer(fake_key, client):
    fake_openai = MagicMock()
    fake_openai.chat.completions.create.return_value = _mock_completion("4")
    with patch("app.ai.OpenAI", return_value=fake_openai):
        resp = client.post("/api/ai/test")
    assert resp.status_code == 200
    assert resp.json() == {"answer": "4"}
    call = fake_openai.chat.completions.create.call_args
    assert call.kwargs["model"] == ai.MODEL
    assert "2+2" in call.kwargs["messages"][0]["content"]


def test_ai_test_endpoint_missing_key(monkeypatch, client):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    resp = client.post("/api/ai/test")
    assert resp.status_code == 500
    assert "OPENROUTER_API_KEY" in resp.json()["detail"]


def test_ai_test_endpoint_handles_openai_error(fake_key, client):
    fake_openai = MagicMock()
    fake_openai.chat.completions.create.side_effect = APIError(
        message="boom", request=MagicMock(), body=None
    )
    with patch("app.ai.OpenAI", return_value=fake_openai):
        resp = client.post("/api/ai/test")
    assert resp.status_code == 502
    assert "OpenRouter error" in resp.json()["detail"]


@pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set; skipping live integration test",
)
def test_ai_test_live_openrouter_call(client):
    resp = client.post("/api/ai/test")
    assert resp.status_code == 200
    assert "4" in resp.json()["answer"]


# ----- Part 9: /api/ai/chat -----


def _mock_parsed(response: str, updates=None):
    c = MagicMock()
    c.choices = [MagicMock(message=MagicMock(parsed=ChatResponse(
        response=response, board_updates=updates or []
    )))]
    return c


def test_chat_requires_auth(client):
    resp = client.post("/api/ai/chat", json={"message": "hi"})
    assert resp.status_code == 401


def test_system_prompt_includes_board_state():
    board = {"columns": [{"id": 1, "title": "Todo", "cardIds": [7]}],
             "cards": {7: {"id": 7, "title": "Thing", "details": "d"}}}
    prompt = build_system_prompt(board)
    assert "Todo" in prompt
    assert "Thing" in prompt
    assert "create_card" in prompt


def test_chat_text_only_response(fake_key, auth_client):
    fake = MagicMock()
    fake.chat.completions.parse.return_value = _mock_parsed("Hello there")
    with patch("app.ai.OpenAI", return_value=fake):
        resp = auth_client.post("/api/ai/chat", json={"message": "hi"})
    assert resp.status_code == 200
    assert resp.json() == {"response": "Hello there", "board_updates": []}


def test_chat_applies_create_card(fake_key, auth_client):
    board = auth_client.get("/api/board").json()
    col_id = board["columns"][0]["id"]
    updates = [BoardUpdate(action="create_card", column_id=col_id, title="AI Card", details="via AI")]
    fake = MagicMock()
    fake.chat.completions.parse.return_value = _mock_parsed("Done", updates)
    with patch("app.ai.OpenAI", return_value=fake):
        resp = auth_client.post("/api/ai/chat", json={"message": "add a card"})
    assert resp.status_code == 200
    after = auth_client.get("/api/board").json()
    titles = [c["title"] for c in after["cards"].values()]
    assert "AI Card" in titles


def test_chat_malformed_response_returns_502(fake_key, auth_client):
    fake = MagicMock()
    c = MagicMock()
    c.choices = [MagicMock(message=MagicMock(parsed=None))]
    fake.chat.completions.parse.return_value = c
    with patch("app.ai.OpenAI", return_value=fake):
        resp = auth_client.post("/api/ai/chat", json={"message": "hi"})
    assert resp.status_code == 502


def test_chat_openai_error_returns_502(fake_key, auth_client):
    fake = MagicMock()
    fake.chat.completions.parse.side_effect = APIError(
        message="boom", request=MagicMock(), body=None
    )
    with patch("app.ai.OpenAI", return_value=fake):
        resp = auth_client.post("/api/ai/chat", json={"message": "hi"})
    assert resp.status_code == 502


def test_chat_conversation_history_maintained(fake_key, auth_client):
    fake = MagicMock()
    fake.chat.completions.parse.side_effect = [
        _mock_parsed("first reply"),
        _mock_parsed("second reply"),
    ]
    with patch("app.ai.OpenAI", return_value=fake):
        auth_client.post("/api/ai/chat", json={"message": "first"})
        auth_client.post("/api/ai/chat", json={"message": "second"})
    second_call_messages = fake.chat.completions.parse.call_args_list[1].kwargs["messages"]
    contents = [m["content"] for m in second_call_messages]
    assert "first" in contents
    assert "first reply" in contents
    assert "second" in contents


def test_apply_update_update_card(test_db, auth_client):
    board = auth_client.get("/api/board").json()
    card_id = next(iter(board["cards"].keys()))
    conn = get_connection()
    user_id = ensure_user(conn, "user")
    apply_update(conn, user_id, BoardUpdate(action="update_card", card_id=int(card_id), title="Renamed"))
    row = conn.execute("SELECT title FROM cards WHERE id = ?", (card_id,)).fetchone()
    conn.close()
    assert row["title"] == "Renamed"


def test_apply_update_delete_card(test_db, auth_client):
    board = auth_client.get("/api/board").json()
    card_id = int(next(iter(board["cards"].keys())))
    conn = get_connection()
    user_id = ensure_user(conn, "user")
    apply_update(conn, user_id, BoardUpdate(action="delete_card", card_id=card_id))
    row = conn.execute("SELECT id FROM cards WHERE id = ?", (card_id,)).fetchone()
    conn.close()
    assert row is None


def test_apply_update_move_card(test_db, auth_client):
    board = auth_client.get("/api/board").json()
    card_id = int(next(iter(board["cards"].keys())))
    target_col = board["columns"][-1]["id"]
    conn = get_connection()
    user_id = ensure_user(conn, "user")
    apply_update(conn, user_id, BoardUpdate(
        action="move_card", card_id=card_id, column_id=target_col, position=0
    ))
    row = conn.execute("SELECT column_id, position FROM cards WHERE id = ?", (card_id,)).fetchone()
    conn.close()
    assert row["column_id"] == target_col
    assert row["position"] == 0


def test_apply_update_ignores_invalid(test_db, auth_client):
    conn = get_connection()
    user_id = ensure_user(conn, "user")
    # missing required fields — should no-op, not raise
    apply_update(conn, user_id, BoardUpdate(action="create_card"))
    apply_update(conn, user_id, BoardUpdate(action="update_card", card_id=99999, title="x"))
    apply_update(conn, user_id, BoardUpdate(action="delete_card", card_id=99999))
    apply_update(conn, user_id, BoardUpdate(
        action="move_card", card_id=99999, column_id=99999, position=0
    ))
    conn.close()


@pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set",
)
def test_chat_live_create_card(auth_client):
    board = auth_client.get("/api/board").json()
    col_id = board["columns"][0]["id"]
    before = len(board["cards"])
    resp = auth_client.post("/api/ai/chat", json={
        "message": f"Add a card titled 'Buy milk' to column {col_id}."
    })
    assert resp.status_code == 200
    after = auth_client.get("/api/board").json()
    assert len(after["cards"]) == before + 1


@pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set",
)
def test_chat_live_text_only(auth_client):
    resp = auth_client.post("/api/ai/chat", json={
        "message": "How many columns are on the board? Answer in one word."
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["response"]
    assert data["board_updates"] == []
