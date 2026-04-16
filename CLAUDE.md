# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Project Management app ("Kanban Studio") with a Next.js frontend and Python FastAPI backend, packaged in Docker. See `AGENTS.md` for full business requirements and `docs/PLAN.md` for the phased build plan.

## Commands

### Frontend (run from `frontend/`)

```bash
npm install              # install dependencies
npm run dev              # dev server on localhost:3000
npm run build            # production build
npm run lint             # eslint
npm run test:unit        # vitest (unit tests in src/**/*.test.{ts,tsx})
npm run test:e2e         # playwright (e2e tests in tests/)
npm run test:all         # unit + e2e
```

### Backend (run from `backend/`)

```bash
uv sync --extra dev      # install dependencies (including dev)
uv run pytest -v --cov=app --cov-report=term-missing  # run tests with coverage
uv run uvicorn app.main:app --reload                   # dev server on localhost:8000
```

### Docker

```bash
scripts/start.sh         # build and start (Mac/Linux)
scripts/stop.sh          # stop (Mac/Linux)
docker compose up --build -d   # or directly via docker compose
```

App runs at `http://localhost:8000`. OpenRouter API key via `OPENROUTER_API_KEY` in `.env`.

## Architecture

- **frontend/**: Next.js 16 app with React 19, Tailwind CSS v4, @dnd-kit for drag-and-drop
- **backend/**: FastAPI server (Python 3.12, uv) serving the statically-built frontend at `/` and API at `/api/`
- **scripts/**: Start/stop scripts for Mac/Linux (.sh) and Windows (.bat)
- **docs/**: Project planning documents

### Frontend structure

- `src/app/` - Next.js app router (single page renders `KanbanBoard`)
- `src/components/` - KanbanBoard, KanbanColumn, KanbanCard, KanbanCardPreview, NewCardForm
- `src/lib/kanban.ts` - Board data types (`Card`, `Column`, `BoardData`), `moveCard` logic, `initialData`, `createId`
- Unit tests use Vitest + Testing Library + jsdom; path alias `@` maps to `src/`
- E2e tests use Playwright against `http://127.0.0.1:3000`
- Fonts: Space Grotesk (display), Manrope (body)

### State management

Currently client-side only with React `useState`. Board state (`BoardData`) holds columns with ordered `cardIds` arrays and a flat `cards` record. The `moveCard` pure function handles all drag-and-drop reordering logic.

## Color Scheme

- Accent Yellow: `#ecad0a`
- Blue Primary: `#209dd7`
- Purple Secondary: `#753991`
- Dark Navy: `#032147`
- Gray Text: `#888888`

## Coding Standards

- Use latest library versions and idiomatic patterns
- Keep it simple -- no over-engineering, no unnecessary defensive programming, no extra features
- Be concise. No emojis ever.
- When hitting issues, identify root cause with evidence before attempting a fix
