from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.auth import router as auth_router

app = FastAPI(title="Kanban Studio API")
app.include_router(auth_router)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@app.get("/api/health")
def health():
    return {"status": "ok"}


if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
