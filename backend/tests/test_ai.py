import os
from unittest.mock import MagicMock, patch

import pytest
from openai import APIError

from app import ai
from app.ai import BoardUpdate, ChatResponse, apply_update, build_system_prompt
from app.db import ensure_default_board, get_connection
from app.users import get_user_by_username


def _mock_completion(content: str):
    completion = MagicMock()
    completion.choices = [MagicMock(message=MagicMock(content=content))]
    return completion


@pytest.fixture
def fake_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")


def _default_board_id() -> int:
    conn = get_connection()
    try:
        user = get_user_by_username(conn, "user")
        assert user is not None
        return ensure_default_board(conn, user["id"])
    finally:
        conn.close()


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
    data = resp.json()
    assert data["response"] == "Hello there"
    assert data["board_updates"] == []
    assert data["applied"] == 0
    assert data["skipped"] == 0
    assert data["board_id"] == _default_board_id()


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
    card_id = int(next(iter(board["cards"].keys())))
    board_id = _default_board_id()
    conn = get_connection()
    apply_update(conn, board_id, BoardUpdate(
        action="update_card", card_id=card_id, title="Renamed"
    ))
    row = conn.execute("SELECT title FROM cards WHERE id = ?", (card_id,)).fetchone()
    conn.close()
    assert row["title"] == "Renamed"


def test_apply_update_delete_card(test_db, auth_client):
    board = auth_client.get("/api/board").json()
    card_id = int(next(iter(board["cards"].keys())))
    board_id = _default_board_id()
    conn = get_connection()
    apply_update(conn, board_id, BoardUpdate(action="delete_card", card_id=card_id))
    row = conn.execute("SELECT id FROM cards WHERE id = ?", (card_id,)).fetchone()
    conn.close()
    assert row is None


def test_apply_update_move_card(test_db, auth_client):
    board = auth_client.get("/api/board").json()
    card_id = int(next(iter(board["cards"].keys())))
    target_col = board["columns"][-1]["id"]
    board_id = _default_board_id()
    conn = get_connection()
    apply_update(conn, board_id, BoardUpdate(
        action="move_card", card_id=card_id, column_id=target_col, position=0
    ))
    row = conn.execute("SELECT column_id, position FROM cards WHERE id = ?", (card_id,)).fetchone()
    conn.close()
    assert row["column_id"] == target_col
    assert row["position"] == 0


def test_apply_update_ignores_invalid(test_db, auth_client):
    board_id = _default_board_id()
    conn = get_connection()
    # missing required fields — should no-op, not raise
    assert not apply_update(conn, board_id, BoardUpdate(action="create_card"))
    assert not apply_update(conn, board_id, BoardUpdate(
        action="update_card", card_id=99999, title="x"
    ))
    assert not apply_update(conn, board_id, BoardUpdate(
        action="delete_card", card_id=99999
    ))
    assert not apply_update(conn, board_id, BoardUpdate(
        action="move_card", card_id=99999, column_id=99999, position=0
    ))
    conn.close()


def test_chat_history_capped(fake_key, auth_client):
    """Conversation history should stay within MAX_HISTORY_TURNS."""
    from app.ai import MAX_HISTORY_TURNS, conversations

    fake = MagicMock()
    fake.chat.completions.parse.side_effect = [
        _mock_parsed(f"r{i}") for i in range(MAX_HISTORY_TURNS)
    ]
    with patch("app.ai.OpenAI", return_value=fake):
        for i in range(MAX_HISTORY_TURNS // 2 + 5):
            auth_client.post("/api/ai/chat", json={"message": f"m{i}"})
    board_id = _default_board_id()
    assert len(conversations[("user", board_id)]) <= MAX_HISTORY_TURNS


def test_clear_conversation(fake_key, auth_client):
    from app.ai import conversations

    fake = MagicMock()
    fake.chat.completions.parse.return_value = _mock_parsed("hi")
    with patch("app.ai.OpenAI", return_value=fake):
        auth_client.post("/api/ai/chat", json={"message": "hello"})
    board_id = _default_board_id()
    assert ("user", board_id) in conversations

    resp = auth_client.delete("/api/ai/conversation")
    assert resp.status_code == 200
    assert ("user", board_id) not in conversations


def test_clear_conversation_requires_auth(client):
    resp = client.delete("/api/ai/conversation")
    assert resp.status_code == 401


def test_chat_returns_applied_and_skipped_counts(fake_key, auth_client):
    board = auth_client.get("/api/board").json()
    col_id = board["columns"][0]["id"]
    updates = [
        BoardUpdate(action="create_card", column_id=col_id, title="ok"),
        BoardUpdate(action="delete_card", card_id=99999),  # missing -> skipped
    ]
    fake = MagicMock()
    fake.chat.completions.parse.return_value = _mock_parsed("done", updates)
    with patch("app.ai.OpenAI", return_value=fake):
        resp = auth_client.post("/api/ai/chat", json={"message": "go"})
    body = resp.json()
    assert body["applied"] == 1
    assert body["skipped"] == 1


def test_chat_scoped_to_board_id(fake_key, auth_client):
    """When board_id is provided explicitly, chat targets that board."""
    # Create a second board
    created = auth_client.post(
        "/api/boards", json={"name": "Side project"}
    ).json()
    target_board_id = created["id"]
    target_full = auth_client.get(f"/api/boards/{target_board_id}").json()
    col_id = target_full["columns"][0]["id"]

    updates = [BoardUpdate(
        action="create_card", column_id=col_id, title="Scoped", details=""
    )]
    fake = MagicMock()
    fake.chat.completions.parse.return_value = _mock_parsed("ok", updates)
    with patch("app.ai.OpenAI", return_value=fake):
        resp = auth_client.post(
            "/api/ai/chat",
            json={"message": "add", "board_id": target_board_id},
        )
    assert resp.status_code == 200
    assert resp.json()["board_id"] == target_board_id

    after = auth_client.get(f"/api/boards/{target_board_id}").json()
    titles = [c["title"] for c in after["cards"].values()]
    assert "Scoped" in titles


def test_chat_unknown_board_id_returns_404(fake_key, auth_client):
    resp = auth_client.post(
        "/api/ai/chat", json={"message": "hi", "board_id": 99999}
    )
    assert resp.status_code == 404


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
