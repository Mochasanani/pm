from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.ai import router as ai_router
from app.auth import router as auth_router
from app.board import router as board_router
from app.db import get_connection, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = get_connection()
    init_db(conn)
    conn.close()
    yield


app = FastAPI(title="Kanban Studio API", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(board_router)
app.include_router(ai_router)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@app.get("/api/health")
def health():
    return {"status": "ok"}


if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
