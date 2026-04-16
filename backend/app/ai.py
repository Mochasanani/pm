import os

from fastapi import APIRouter, HTTPException
from openai import OpenAI, OpenAIError

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
