# Code Review — Kanban Studio

Scope: full repo review (backend, frontend, infra, tests, docs) as of commit `47b014f` (Part 10 complete).
Verdict: the app is functional and well-tested for an MVP. Highest-impact issues cluster around (1) column-rename firing an API call per keystroke, (2) `ai.py` calling a route handler as a function and duplicating board-mutation logic, (3) no DB connection cleanup on exception paths, and (4) the AI chat endpoint can mutate the board with zero guardrails against prompt injection.

Findings are tagged **[P1]** (should fix before any further feature work), **[P2]** (fix soon, correctness/quality), **[P3]** (nice to have / polish).

---

## Backend

### [P1] `ai.py` imports and calls a FastAPI route handler as a plain function
`app/ai.py:166` does `board = get_board(username=username)`. `get_board` is an HTTP handler defined in `board.py`; calling it directly works today only because the dependency-injected parameter has a default. This couples two routers, makes `ai.py` untestable without importing `board.py`, and will break as soon as `get_board` grows a second dependency.

**Action:** extract a pure function `load_board(username: str) -> dict` in `db.py` (or a new `app/services.py`) and have both `board.get_board` and `ai.ai_chat` call it.

### [P1] Duplicated board-mutation logic between `board.py` and `ai.py`
`apply_update` in `ai.py` re-implements move/delete/create semantics already in `board.py` (position renumbering, ownership checks). Any fix to one must be mirrored in the other — this has already happened silently (e.g. `create_card`'s `"No details yet."` fallback is duplicated).

**Action:** extract `create_card(conn, user_id, column_id, title, details)`, `update_card(...)`, `delete_card(...)`, `move_card(...)` as service functions in `db.py` or `app/board_service.py`. Both routers call the same service.

### [P1] DB connection leaks on exception paths
Every `board.py` handler follows the pattern `conn = get_connection(); ... conn.close()` with the close only reached on the success path. Any SQL error, pydantic validation error, or `HTTPException` leaves the connection open. SQLite recovers because connections are per-request and the process lives, but this is still a latent resource leak.

**Action:** use a FastAPI dependency that yields a connection and closes it in a `finally` block:
```python
def db_conn():
    conn = get_connection()
    try: yield conn
    finally: conn.close()
```
Then `def get_board(..., conn=Depends(db_conn))`.

### [P2] Column rename is silently permissive
`RenameColumnRequest.title` has no min length, so `PUT /api/board/columns/{id}` happily accepts `""`. Same for `create_card` / `update_card` titles. The frontend guards against empty on card creation but not on column rename.

**Action:** add `Field(min_length=1, max_length=200)` to `title` on all request models. Reject empty titles at the API boundary.

### [P2] `create_card` silently substitutes details
`board.py:97` and `ai.py:95` both coerce empty details to `"No details yet."`. Users who intentionally leave details blank get content they didn't write, which later looks like real data when editing. This is a surprising side effect; details should default to `""`.

**Action:** remove the `or "No details yet."` fallback; store `""` when empty.

### [P2] `ai_chat` conversation store grows without bound
`conversations: dict[str, list[dict]]` is append-only per username, in memory, across every chat call. A long session eventually exceeds the model context window (the full history is shipped every call plus the full board JSON in the system prompt). There's also no way for the user to clear it.

**Action:** cap history to the last N (e.g. 20) turns, and add `DELETE /api/ai/conversation` wired to a "Clear chat" button.

### [P2] AI endpoint mutates the DB with no guardrails
Any message sent to `/api/ai/chat` can return `board_updates` that immediately delete cards or move them, with no user confirmation, no rate limiting, and no audit log. Combined with the fact that the **board state is embedded in the system prompt**, a card whose title/details contains adversarial text (e.g. a shared board in the future) could instruct the AI to delete other cards — classic prompt injection.

**Action (MVP):** at minimum, log every applied update with user, timestamp, and payload. Longer-term: require client confirmation for destructive actions (`delete_card`), or return a "proposed changes" payload that the UI confirms before a second call applies them.

### [P2] Login hands out unlimited sessions, no rate limiting
`POST /api/login` has no throttling and the session store grows forever (each login creates a new token even for the same user; old tokens never expire). For a single-user MVP this is benign, but `sessions` leaks across test runs inside one process and across long-running prod instances.

**Action:** invalidate prior tokens for the same user on login, or add a simple TTL on tokens. Document that the store is ephemeral (lost on restart — which is actually already a forcing function, but worth stating).

### [P3] `main.py` lifespan opens a DB connection solely to close it
```python
conn = get_connection()
init_db(conn)
conn.close()
```
`init_db` is the only operation; wrap it so the lifespan doesn't need to know about connection objects: `init_db()` could call `get_connection()` internally.

### [P3] Session cookie lacks `secure=True` guard for production
Fine for localhost, but a prod build will send cookies over HTTP. Make it conditional on an env var (`COOKIE_SECURE`).

### [P3] No CSRF protection
`samesite=lax` prevents the common cases, but adding a CSRF token would be standard defense-in-depth for the POST endpoints.

### [P3] `apply_update` silently no-ops on invalid IDs
Documented in PLAN.md as intentional, but from a UX perspective the AI reports "done" while nothing happened. Consider returning an `applied`/`skipped` count and surfacing it in the chat reply.

---

## Frontend

### [P1] Column rename fires an API call on every keystroke
`KanbanColumn.tsx:46` wires `onChange={(e) => onRename(column.id, e.target.value)}`, and `KanbanBoard.handleRenameColumn` calls `renameColumnApi` immediately. Typing "Planning" sends 8 PUT requests. This is wasteful now and becomes broken when latency > keystroke interval (out-of-order responses).

**Action:** either debounce (500ms) or rename on blur / Enter only. The e2e test already uses Tab-to-blur, so switching to `onBlur` would not break tests and is the simplest fix.

### [P2] `API_BASE` detection is fragile
```ts
typeof window !== "undefined" && window.location.origin !== "http://localhost:3000"
  ? "" : "http://localhost:8000";
```
Any other dev origin (127.0.0.1, .local domain, preview build) silently points at port 8000 or breaks. Also, the cross-origin dev mode needs CORS on the backend (currently not configured) and `samesite=lax` cookies **will** drop on cross-origin requests in modern browsers.

**Action:** use an env var (`NEXT_PUBLIC_API_BASE`, empty by default) and set it only in the dev script. Add CORS middleware conditional on dev mode.

### [P2] `lib/auth.ts` is a dead re-export
```ts
export { login, logout, getMe } from "./api";
```
One line, one file, no value. Either delete it and update imports, or inline the auth functions here.

**Action:** delete `lib/auth.ts` and import from `lib/api.ts` directly.

### [P2] `lib/kanban.ts` still exports `initialData` and `createId` — both dead code post-Part-7
The board is loaded from the API, so `initialData` is orphaned and its card text drifts from the backend seed data. `createId` is only used for in-memory IDs that no longer exist.

**Action:** delete both exports and the associated test (`kanban.test.ts` tests `moveCard` only — confirm, then delete dead exports).

### [P2] `handleDragEnd` reads from stale `board` reference
```ts
if (active.id !== over.id) { setBoard({ ...board, columns: newColumns }); }
const targetCol = board.columns.find((col) => col.cardIds.includes(cardId));
```
The `board.columns` read on the line after `setBoard` is the *pre-update* state (React state is immutable; `board` was captured at render time). In practice this usually matches because `handleDragOver` already moved the card, but the dependency on side-effect ordering is subtle. Compute `newColumns` once, then use *that* local variable to derive the position.

**Action:**
```ts
const newColumns = moveCard(board.columns, active.id, over.id);
setBoard({ ...board, columns: newColumns });
const targetCol = newColumns.find(c => c.cardIds.includes(cardId));
```

### [P3] `isDragTarget` expression is hard to read
`KanbanBoard.tsx:265` is a one-line conditional with four `.find` / `.includes` calls. Extract to a named helper (`wasNotOriginalColumn(column, cardId, preDragBoard)`) or memoize.

### [P3] `AiSidebar` error state never clears on success
`setError(null)` only runs at the start of `handleSend`. After an error, the banner stays visible until the next send. Clear it on successful render too.

### [P3] No visual indicator that AI applied destructive changes
The assistant replies "done", the board refetches, and cards quietly disappear. Consider a transient toast: "AI moved 1 card, deleted 1 card."

---

## Infrastructure / Docker

### [P2] Docker volume persists DB across test runs — caused today's e2e flake
`docker-compose.yml` mounts named volume `pm-data:/app/data`. Running e2e twice without `docker compose down -v` fails the "5 columns, 8 cards" assertion because the first run mutated the board. This cost us a confused debug cycle in the last session.

**Action:** either (a) add a `scripts/test-e2e.sh` that does `docker compose down -v && up -d` before running Playwright, or (b) add a `POST /api/dev/reset` endpoint (gated by env var) that tests can call.

### [P2] `Dockerfile` uses `uv:latest` and has a silent fallback
```
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev
```
`uv:latest` breaks reproducibility. The `|| uv sync --no-dev` silently re-resolves the lock on mismatch, which defeats `--frozen`'s purpose.

**Action:** pin uv to a specific tag (`ghcr.io/astral-sh/uv:0.5.x`), and remove the fallback — if `--frozen` fails, the build should fail loudly.

### [P3] No healthcheck in compose; container runs as root
Add:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
  interval: 10s
```
And add a non-root user stage to the Dockerfile.

### [P3] `network: host` at build stage is a workaround, not a fix
Documented in PLAN.md as needed for Google Fonts download. Consider `next/font/local` or preloading the fonts into the image so the build doesn't need host networking.

---

## Tests

### [P2] E2e persistence drag-and-drop test is flaky
Confirmed in the prior session — passed on retry with a fresh volume. Raw mouse events with Playwright + @dnd-kit are sensitive to layout/animation timing.

**Action:** either (a) use Playwright's `dispatchEvent` / keyboard-driven sort (@dnd-kit supports keyboard sensors), or (b) add `retries: 2` in `playwright.config.ts` for the CI path. Option (a) is more durable.

### [P3] Backend coverage is 92% but `main.py` lifespan is untested
`app/main.py:15-18` is uncovered. A simple test that calls `TestClient(app)` with a temp DB and asserts `init_db` ran would close the gap.

### [P3] AI live-call tests are skipped by default
`tests/test_ai.py` has `test_ai_test_live_openrouter_call` and two live chat tests that skip without `OPENROUTER_API_KEY`. Consider a `make test-live` target or a dedicated marker so it's easy to run intentionally.

---

## Documentation

### [P3] AGENTS.md and CLAUDE.md duplicate some content
Both describe the project and commands. Consolidate or cross-link.

### [P3] No architecture diagram or request-flow sketch
`DATABASE.md` is solid. A similarly short `ARCHITECTURE.md` covering the auth/session flow and AI pipeline would help future contributors.

---

## Summary of recommended action order

1. **Debounce / onBlur the column rename** (P1 frontend, ~15 min).
2. **Extract `load_board` and service functions** to kill the `get_board` function-call-as-handler and the duplicated mutation logic between `board.py` and `ai.py` (P1 backend, ~1 hr).
3. **Wrap DB connections in a `finally`/`Depends(db_conn)`** (P1 backend, ~30 min).
4. **Fix volume/test interaction** — either test-reset script or `down -v` in the e2e runner (P2, ~15 min).
5. **Cap AI conversation history + add clear button** (P2, ~30 min).
6. **Remove dead code** (`lib/auth.ts`, `initialData`, `createId`, `"No details yet."` fallback) (P2, ~20 min).
7. **Pin `uv` version, remove silent fallback** (P2, ~5 min).
8. **Tighten pydantic validation** (min_length on titles) (P2, ~15 min).
9. Everything else in P3.
