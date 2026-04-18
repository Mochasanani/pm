# Project Plan

## Testing Standards (all parts)

- Target 80% unit test coverage where sensible; focus on valuable tests over hitting the number
- Robust integration/e2e tests for every user-facing feature
- Each part must pass all tests from previous parts (no regressions)

---

## Part 1: Plan

- [x] Enrich this document with detailed substeps, checklists, tests and success criteria
- [x] Create `frontend/AGENTS.md` describing existing frontend code
- [x] Get user approval on the plan

**Success criteria:** Plan is comprehensive and approved. Frontend codebase is documented.

---

## Part 2: Scaffolding

Set up Docker infrastructure, FastAPI backend, and start/stop scripts. Serve example static HTML and confirm a hello world API call works.

- [x] Create `backend/` Python project with `pyproject.toml` using `uv`
- [x] Create FastAPI app in `backend/` with a health check endpoint (`GET /api/health`)
- [x] Create `Dockerfile` at project root
  - [x] Multi-stage build: Node for frontend static build, Python for backend
  - [x] Use `uv` to install Python dependencies
  - [x] Serve a placeholder `index.html` at `/` via FastAPI static files
- [x] Create `docker-compose.yml` (single service, port mapping, .env passthrough)
- [x] Create `scripts/start.sh` (Mac/Linux) and `scripts/start.bat` (Windows)
- [x] Create `scripts/stop.sh` (Mac/Linux) and `scripts/stop.bat` (Windows)
- [x] Make scripts executable and handle common cases (container already running, etc.)

**Tests:**
- [x] Backend unit test: `GET /api/health` returns 200 with expected JSON
- [x] Integration test: `docker compose up` builds and starts successfully (requires Docker)
- [x] Integration test: `curl http://localhost:8000/` returns placeholder HTML (requires Docker)
- [x] Integration test: `curl http://localhost:8000/api/health` returns 200 (requires Docker)

**Success criteria:** `scripts/start.sh` brings up the Docker container. Browser shows placeholder page at `localhost:8000`. API health endpoint responds.

---

## Part 3: Add in Frontend

Build the Next.js frontend statically and serve it via FastAPI, so the demo Kanban board displays at `/`.

- [x] Configure Next.js for static export (`output: 'export'` in `next.config.ts`)
- [x] Update `Dockerfile` to run `npm run build` and copy static output to backend's static directory
- [x] Configure FastAPI to serve the static build at `/` (with correct asset paths)
- [x] Verify all existing frontend features work when served statically

**Tests:**
- [x] Frontend unit tests: all existing tests pass (maintain >=80% coverage)
- [x] E2e test: board loads with 5 columns and 8 cards at `localhost:8000`
- [x] E2e test: card drag-and-drop works
- [x] E2e test: column rename works
- [x] E2e test: add and remove card works
- [x] Integration test: Docker build succeeds with frontend included

**Success criteria:** Running `scripts/start.sh` shows the full Kanban board at `localhost:8000`. All unit and e2e tests pass.

---

## Part 4: Fake User Sign In

Add login screen with hardcoded credentials ("user", "password") and logout functionality.

- [x] Add `POST /api/login` endpoint (validates credentials, sets session cookie)
- [x] Add `POST /api/logout` endpoint (clears session cookie)
- [x] Add `GET /api/me` endpoint (returns current user or 401)
- [x] Create login page component in frontend
  - [x] Username and password fields
  - [x] Error message on invalid credentials
  - [x] Redirect to board on success
- [x] Add auth guard: unauthenticated users see login page, authenticated users see board
- [x] Add logout button to board header
- [x] Style login page using project color scheme

**Tests:**
- [x] Backend unit: `POST /api/login` with valid credentials returns 200 + sets cookie
- [x] Backend unit: `POST /api/login` with invalid credentials returns 401
- [x] Backend unit: `GET /api/me` with valid session returns user info
- [x] Backend unit: `GET /api/me` without session returns 401
- [x] Backend unit: `POST /api/logout` clears session
- [x] E2e test: full login flow (visit -> login page -> enter credentials -> see board)
- [x] E2e test: invalid credentials show error, stay on login page
- [x] E2e test: logout returns to login page
- [x] E2e test: unauthenticated visit shows login page (replaces "direct navigation redirects")

**Design decisions:**
- Auth is client-side: page.tsx calls `GET /api/me` on load, shows LoginPage or KanbanBoard
- Session cookies are httponly with samesite=lax
- KanbanBoard accepts `user` and `onLogout` props from the auth guard in page.tsx

**Success criteria:** Unauthenticated users see login page. "user"/"password" grants access to the board. Logout works. All tests pass.

---

## Part 5: Database Modeling

Propose a database schema for the Kanban, document it, and get user approval.

- [x] Design SQLite schema supporting:
  - [x] Multiple users (for future, but MVP uses one)
  - [x] One board per user
  - [x] Columns with ordering and custom titles
  - [x] Cards with title, details, and ordering within columns
- [x] Save proposed schema as `docs/schema.json`
- [x] Write `docs/DATABASE.md` explaining the schema, relationships, and design decisions
- [x] Get user sign-off on schema before proceeding

**Success criteria:** Schema documented and approved. Supports the current feature set and the multi-user future requirement.

---

## Part 6: Backend API

Add API routes for reading and modifying the Kanban board. Database auto-creates if missing.

- [x] Implement database initialization (create tables if not exist on startup)
- [x] Seed default board data for new users on first login
- [x] `GET /api/board` -- returns the full board (columns + cards) for the logged-in user
- [x] `PUT /api/board/columns/:id` -- rename a column
- [x] `POST /api/board/cards` -- create a card in a column
- [x] `PUT /api/board/cards/:id` -- update a card's title/details
- [x] `DELETE /api/board/cards/:id` -- delete a card
- [x] `PUT /api/board/cards/:id/move` -- move a card to a column at a position
- [x] All endpoints require authentication (return 401 if not logged in)

**Tests:**
- [x] Unit test each endpoint with valid and invalid inputs
- [x] Unit test authentication enforcement on every endpoint
- [x] Unit test database auto-creation from scratch
- [x] Unit test default board seeding for a new user
- [x] Integration test: full CRUD cycle (create card, read board, update card, move card, delete card)
- [x] Backend test coverage at 91%

**Design decisions:**
- SQLite with sync `sqlite3` (adequate for single-user MVP scale)
- DB auto-creates on FastAPI lifespan startup; board seeds on first login
- In-memory session store (tokens via `secrets.token_urlsafe`)
- Integer `position` fields for ordering; renumbered on move/delete
- Test fixtures use `tmp_path` for isolated per-test SQLite databases

**Success criteria:** All board CRUD operations work via API. Database is created automatically. All endpoints are auth-protected. Tests pass.

---

## Part 7: Frontend + Backend Integration

Connect the frontend to the backend API so the Kanban board persists data.

- [x] Replace in-memory `initialData` with API fetch on board load (`GET /api/board`)
- [x] Wire column rename to `PUT /api/board/columns/:id`
- [x] Wire add card to `POST /api/board/cards`
- [x] Wire delete card to `DELETE /api/board/cards/:id`
- [x] Wire drag-and-drop move to `PUT /api/board/cards/:id/move`
- [x] Add loading and error states to the UI
- [x] Handle optimistic updates with rollback on API failure

**Tests:**
- [x] Frontend unit: board fetches data from API on mount (mocked)
- [x] E2e test: create a card, refresh page, card persists
- [x] E2e test: rename column, refresh page, name persists
- [x] E2e test: move card, refresh page, position persists
- [x] E2e test: delete card, refresh page, card is gone

**Design decisions:**
- Consolidated all API calls (auth + board) into `src/lib/api.ts`
- Backend returns numeric IDs; frontend converts to strings in the API layer to minimize component changes
- Optimistic updates: UI updates immediately, rolls back on API failure
- Drag-and-drop uses `closestCenter` collision detection (not `closestCorners`) for more accurate targeting
- Live reordering via `onDragOver`: cards shift in real-time during drag to show insertion point
- Dragged card placeholder is hidden (`opacity-0`) so the gap is visible
- Columns highlight with yellow ring when a card is dragged into them
- `docker-compose.yml` uses `network: host` for build stage to allow Google Fonts download during Next.js build
- Playwright e2e tests run with `workers: 1` to avoid session store interference between parallel tests
- `vitest.config.ts` scopes coverage to `src/` only (excludes build artifacts and config files)
- Playwright config supports `BASE_URL` env var: defaults to port 3000 (dev), set to 8000 for Docker testing

**Success criteria:** All board operations persist to the database. Page refresh preserves state. All tests pass.

---

## Part 8: AI Connectivity

Enable the backend to make AI calls via OpenRouter. Verify with a simple test.

- [x] Add OpenRouter client using the OpenAI-compatible API
- [x] Read `OPENROUTER_API_KEY` from environment / `.env`
- [x] Configure model: `openai/gpt-oss-120b`
- [x] Create `POST /api/ai/test` endpoint that sends "What is 2+2?" and returns the response
- [x] Add error handling for missing API key, network errors, rate limits

**Tests:**
- [x] Unit test: AI client constructs correct request to OpenRouter
- [x] Unit test: endpoint returns AI response on success
- [x] Unit test: endpoint returns appropriate error when API key missing
- [x] Unit test: endpoint handles OpenRouter errors gracefully
- [x] Integration test: actual API call to OpenRouter succeeds (skipped when OPENROUTER_API_KEY not set)

**Design decisions:**
- Uses official `openai` Python SDK pointed at `https://openrouter.ai/api/v1`
- `/api/ai/test` is unauthenticated — kept as a permanent connectivity/health check
- Missing key returns 500; OpenAI SDK errors return 502

**Success criteria:** `POST /api/ai/test` returns a correct answer from the AI. Error cases handled.

---

## Part 9: AI Structured Outputs for Kanban

Extend AI calls to include board context and return structured responses that can modify the board.

- [x] Define structured output schema: `{ response: string, board_updates?: BoardUpdate[] }`
- [x] `BoardUpdate` types: create_card, update_card, delete_card, move_card
- [x] `POST /api/ai/chat` endpoint:
  - [x] Accepts user message and conversation history
  - [x] Sends system prompt with current board JSON + user message
  - [x] Parses structured output from AI
  - [x] Applies board updates to database if present
  - [x] Returns AI response text and applied changes
- [x] Store conversation history per session

**Tests:**
- [x] Unit test: system prompt includes current board state
- [x] Unit test: structured output parsing handles valid responses
- [x] Unit test: structured output parsing rejects malformed responses
- [x] Unit test: board updates are applied correctly to database
- [x] Unit test: conversation history is maintained across messages
- [x] Integration test: AI responds with board modifications that are applied
- [x] Integration test: AI responds with text-only answer when no board changes needed

**Design decisions:**
- Single flat `BoardUpdate` model with `action` literal + optional fields (simpler JSON schema than discriminated union)
- Conversation history kept in-memory per username (`ai.conversations` dict), cleared on server restart
- `apply_update` validates user ownership and silently no-ops on invalid/missing IDs rather than raising
- Uses `client.chat.completions.parse(response_format=ChatResponse)` for structured output via pydantic

**Success criteria:** AI can read the board, answer questions about it, and modify it via structured outputs. Changes persist in the database.

---

## Part 10: AI Chat Sidebar

Add a sidebar UI for AI chat that can update the board in real time.

- [x] Create collapsible sidebar component (right side of board)
- [x] Chat message list with user/AI message distinction
- [x] Text input with send button
- [x] Display AI responses with markdown rendering (via `react-markdown`)
- [x] When AI returns board updates, apply them to the UI immediately (refetch board)
- [x] Auto-scroll to latest message
- [x] Loading indicator while AI is responding
- [x] Style sidebar using project color scheme
- [x] Sidebar toggle button in board header

**Tests:**
- [x] Frontend unit: sidebar renders and toggles open/closed
- [x] Frontend unit: sending a message calls the chat API
- [x] Frontend unit: AI response displays in message list
- [x] Frontend unit: board updates from AI trigger a board reload
- [x] Frontend unit: loading state shows while waiting for AI
- [x] E2e test: open sidebar, send message, receive response
- [x] E2e test: AI creates a card via chat, card appears on board
- [x] E2e test: sidebar closes via Close button
- [x] E2e test: conversation history maintained across messages

**Design decisions:**
- Used `react-markdown` for assistant replies; user messages are plain text
- Sidebar is a fixed right drawer, toggled from the board header ("Ask AI" button)
- On replies containing `board_updates`, frontend calls `loadBoard()` to refetch rather than applying updates locally — simpler, always consistent
- E2e tests mock `/api/ai/chat` via Playwright route interception (no network/API key needed); the "AI-created card" test still uses real backend endpoints to simulate the board-state change
**Success criteria:** Sidebar chat works end-to-end. AI can read and modify the board through conversation. UI updates reflect AI changes immediately. All tests pass.

---

## Part 11: Real Users + Multiple Boards (backend)

Replace the hardcoded demo auth with real user accounts, and allow each user to own many boards.

- [x] Expand the `users` table: `email`, `password_hash`, `display_name`, `created_at`
- [x] Hash passwords with `bcrypt`; seed the demo `user` / `password` account
- [x] Add a `boards` table (`user_id`, `name`, `description`, `position`, timestamps); cascade deletes
- [x] Re-parent `columns` from `user_id` to `board_id`
- [x] `POST /api/register` — username + password (+ optional email / display name); 201 on success, 409 on duplicates, 422 on weak inputs
- [x] `GET/PUT /api/me` — fetch / update display name, email, password
- [x] `GET /api/boards`, `POST /api/boards`, `GET/PUT/DELETE /api/boards/{id}` — boards CRUD with per-user isolation
- [x] `PUT /api/boards/{id}/columns/{column_id}` + card endpoints scoped under `/api/boards/{id}/...`
- [x] Keep legacy `/api/board*` endpoints as a thin shim over the user's default board
- [x] AI `/api/ai/chat` accepts optional `board_id` and scopes conversation history by `(username, board_id)`

**Tests:**
- [x] Unit + integration tests for registration (success, conflict, validation, default-board seeding)
- [x] Unit tests for profile update (display name, password change, email conflict)
- [x] Tests for multi-board CRUD with cross-user isolation (alice cannot touch user's boards)
- [x] Tests for scoped card/column ops rejecting cross-board IDs
- [x] AI chat tests for scoped `board_id`
- [x] Backend coverage stays >= 90% (currently 94%)

**Success criteria:** New users can register. Each user sees only their own boards. All existing single-board flows keep working through the legacy shim.

---

## Part 12: Multi-Board Frontend

Wire the frontend to the new APIs so users can register, switch, create, rename and delete boards.

- [x] Update `api.ts` to expose `register`, `updateMe`, `listBoards`, `createBoard`, `renameBoard`, `deleteBoard`
- [x] Add a register mode to the login page
- [x] Add a `BoardSwitcher` with create / rename / delete in the header
- [x] Persist the "currently selected" board id (`localStorage`) and use it for all mutations
- [x] Thread `board_id` through the AI sidebar and conversation clear

**Tests:**
- [x] Unit: board switcher renders the current board name, lists alternatives, creates / renames / deletes
- [x] Unit: switching boards refetches content via `fetchBoardById`
- [x] E2e (`multi-board.spec.ts`): register, create second board, switch between them; users can't see each other's boards

**Design decisions:**
- The frontend uses the new `/api/boards/*` endpoints exclusively; the legacy `/api/board*` shim is still there but unused by the UI.
- The `cards` map now keys on string ids to minimize churn from the earlier single-board code; `api.ts` normalizes ids at the boundary.

**Success criteria:** Users can register, sign in, and manage multiple boards. All mutations target the currently selected board. No regressions.

---

## Part 13: Legacy Schema Migration

Existing Docker volumes hold the single-board schema from Part 6; those installs must upgrade in place without losing data.

- [x] `migrate_legacy_schema` adds missing `users` columns (`email`, `password_hash`, `display_name`, `created_at`)
- [x] Creates the `boards` table, backfills one default board per user, re-parents `columns` from `user_id` to `board_id`
- [x] Rebuild of the `columns` table uses `conn.commit(); PRAGMA foreign_keys=OFF` around the drop so cascading does not wipe `cards`
- [x] Adds `cards.created_at`, `updated_at`, `due_date` on legacy DBs
- [x] `init_db` runs the migration before `CREATE TABLE IF NOT EXISTS` so fresh installs are unaffected

**Tests:**
- [x] `test_migration.py`: legacy DB → boards created, cards preserved; `init_db` idempotent; no-op on fresh DB

**Success criteria:** Existing Docker volumes boot cleanly and keep their cards; fresh installs are unchanged.

---

## Part 14: Card Details, Due Dates, and Profile

Richer card editing and a profile editor off the board header.

- [x] `CardEditModal`: full card editor with title, details, due date picker, delete action, `Escape` / click-outside close
- [x] `cards.due_date` column (`YYYY-MM-DD`), validated on the backend with regex + `date.fromisoformat`
- [x] `UNSET` sentinel + `model_fields_set` so PATCH distinguishes "leave alone" from "set null"
- [x] Due-date badge on `KanbanCard` with `overdue` / `soon` / `ok` color states
- [x] `ProfileModal` off the header: update `display_name`, `email`, `password` via `PUT /api/me`

**Tests:**
- [x] Backend: create-with-due-date, reject-bad-date (422), set/clear via PATCH, omit-leaves-untouched
- [x] Frontend: open modal, save title/details/due-date; due-date badge renders; profile modal saves display name

**Success criteria:** Cards carry due dates that round-trip through the API and render as status badges. Users can edit their profile from the header.

---

## Part 15: Labels

Per-board labels with color, assignable to cards.

- [x] `labels` + `card_labels` tables (cascade delete on board and card)
- [x] `services.py`: `list_labels`, `create_label`, `update_label`, `delete_label`, `set_card_labels` with cross-board validation
- [x] `load_board` batch-queries assignments and returns `labels` + per-card `label_ids`
- [x] REST: `GET/POST /api/boards/{id}/labels`, `PUT/DELETE /api/boards/{id}/labels/{label_id}`, `PUT /api/boards/{id}/cards/{card_id}/labels`
- [x] Color validated as `#RRGGBB`
- [x] Frontend: `Label` type, API client (`listLabels`, `createLabel`, `updateLabel`, `deleteLabel`, `setCardLabels`)
- [x] Label chips on `KanbanCard`; toggle picker in `CardEditModal` that only fires `setCardLabels` when the set actually changed

**Tests:**
- [x] Backend: empty list, CRUD, bad color (422), round-trip via `load_board`, delete removes assignments, cross-board label rejected (404)
- [x] Frontend: toggling a label chip in the edit modal calls `setCardLabels` with the new ids

**Success criteria:** Users can define colored labels per board and attach multiple labels to each card. Labels are isolated per board.

---

## Part 16: Search and Filter

Narrow the board by keyword and by labels.

- [x] Header `Search cards` input filters by `title + details` substring (case-insensitive)
- [x] Label filter row renders a chip per label; clicking toggles membership in the active filter set (AND semantics)
- [x] Filtering hides cards from all columns at once while leaving the underlying board state untouched (drag still works on visible cards)

**Tests:**
- [x] Frontend: typing in search narrows visible cards
- [x] Frontend: clicking a label filter chip narrows to cards carrying that label

**Success criteria:** Users can find cards by keyword or label on any board without navigating away. All prior tests still pass.
