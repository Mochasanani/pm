import os
from unittest.mock import MagicMock, patch

import pytest
from openai import APIError

from app import ai


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
