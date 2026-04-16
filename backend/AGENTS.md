# Backend: Kanban Studio API

## Stack

- Python 3.12, FastAPI
- uv for package management
- SQLite for database (planned)
- uvicorn as ASGI server

## Structure

- `app/main.py` -- FastAPI app. Mounts static files at `/` (serves frontend build). Health endpoint at `GET /api/health`.
- `static/` -- placeholder HTML, replaced by frontend static export during Docker build
- `tests/` -- pytest tests using FastAPI's TestClient

## Commands

```bash
uv sync --extra dev    # install dependencies (including dev)
uv run pytest -v --cov=app --cov-report=term-missing   # run tests with coverage
uv run uvicorn app.main:app --reload                    # run dev server on port 8000
```

## Key Patterns

- Static files are conditionally mounted only if `static/` directory exists
- API routes are prefixed with `/api/`
- Tests use `fastapi.testclient.TestClient` (backed by httpx)
