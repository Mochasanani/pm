# Project Plan

## Testing Standards (all parts)

- Minimum 80% unit test coverage (statements)
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

**Success criteria:** Unauthenticated users see login page. "user"/"password" grants access to the board. Logout works. All tests pass.

---

## Part 5: Database Modeling

Propose a database schema for the Kanban, document it, and get user approval.

- [ ] Design SQLite schema supporting:
  - [ ] Multiple users (for future, but MVP uses one)
  - [ ] One board per user
  - [ ] Columns with ordering and custom titles
  - [ ] Cards with title, details, and ordering within columns
- [ ] Save proposed schema as `docs/schema.json`
- [ ] Write `docs/DATABASE.md` explaining the schema, relationships, and design decisions
- [ ] Get user sign-off on schema before proceeding

**Success criteria:** Schema documented and approved. Supports the current feature set and the multi-user future requirement.

---

## Part 6: Backend API

Add API routes for reading and modifying the Kanban board. Database auto-creates if missing.

- [ ] Implement database initialization (create tables if not exist on startup)
- [ ] Seed default board data for new users on first login
- [ ] `GET /api/board` -- returns the full board (columns + cards) for the logged-in user
- [ ] `PUT /api/board/columns/:id` -- rename a column
- [ ] `POST /api/board/cards` -- create a card in a column
- [ ] `PUT /api/board/cards/:id` -- update a card's title/details
- [ ] `DELETE /api/board/cards/:id` -- delete a card
- [ ] `PUT /api/board/cards/:id/move` -- move a card to a column at a position
- [ ] All endpoints require authentication (return 401 if not logged in)

**Tests:**
- [ ] Unit test each endpoint with valid and invalid inputs
- [ ] Unit test authentication enforcement on every endpoint
- [ ] Unit test database auto-creation from scratch
- [ ] Unit test default board seeding for a new user
- [ ] Integration test: full CRUD cycle (create card, read board, update card, move card, delete card)
- [ ] Maintain >=80% backend test coverage

**Success criteria:** All board CRUD operations work via API. Database is created automatically. All endpoints are auth-protected. Tests pass with >=80% coverage.

---

## Part 7: Frontend + Backend Integration

Connect the frontend to the backend API so the Kanban board persists data.

- [ ] Replace in-memory `initialData` with API fetch on board load (`GET /api/board`)
- [ ] Wire column rename to `PUT /api/board/columns/:id`
- [ ] Wire add card to `POST /api/board/cards`
- [ ] Wire delete card to `DELETE /api/board/cards/:id`
- [ ] Wire drag-and-drop move to `PUT /api/board/cards/:id/move`
- [ ] Add loading and error states to the UI
- [ ] Handle optimistic updates with rollback on API failure

**Tests:**
- [ ] Frontend unit: board fetches data from API on mount
- [ ] Frontend unit: each operation calls the correct API endpoint
- [ ] Frontend unit: loading state displays while fetching
- [ ] Frontend unit: error state displays on API failure
- [ ] E2e test: create a card, refresh page, card persists
- [ ] E2e test: rename column, refresh page, name persists
- [ ] E2e test: move card, refresh page, position persists
- [ ] E2e test: delete card, refresh page, card is gone
- [ ] E2e test: two browser tabs see consistent state after refresh
- [ ] Maintain >=80% coverage across frontend and backend

**Success criteria:** All board operations persist to the database. Page refresh preserves state. All tests pass.

---

## Part 8: AI Connectivity

Enable the backend to make AI calls via OpenRouter. Verify with a simple test.

- [ ] Add OpenRouter client using the OpenAI-compatible API
- [ ] Read `OPENROUTER_API_KEY` from environment / `.env`
- [ ] Configure model: `openai/gpt-oss-120b`
- [ ] Create `POST /api/ai/test` endpoint that sends "What is 2+2?" and returns the response
- [ ] Add error handling for missing API key, network errors, rate limits

**Tests:**
- [ ] Unit test: AI client constructs correct request to OpenRouter
- [ ] Unit test: endpoint returns AI response on success
- [ ] Unit test: endpoint returns appropriate error when API key missing
- [ ] Unit test: endpoint handles OpenRouter errors gracefully
- [ ] Integration test: actual API call to OpenRouter succeeds (can be skipped in CI without key)

**Success criteria:** `POST /api/ai/test` returns a correct answer from the AI. Error cases handled.

---

## Part 9: AI Structured Outputs for Kanban

Extend AI calls to include board context and return structured responses that can modify the board.

- [ ] Define structured output schema: `{ response: string, board_updates?: BoardUpdate[] }`
- [ ] `BoardUpdate` types: create_card, update_card, delete_card, move_card
- [ ] `POST /api/ai/chat` endpoint:
  - [ ] Accepts user message and conversation history
  - [ ] Sends system prompt with current board JSON + user message
  - [ ] Parses structured output from AI
  - [ ] Applies board updates to database if present
  - [ ] Returns AI response text and applied changes
- [ ] Store conversation history per session

**Tests:**
- [ ] Unit test: system prompt includes current board state
- [ ] Unit test: structured output parsing handles valid responses
- [ ] Unit test: structured output parsing rejects malformed responses
- [ ] Unit test: board updates are applied correctly to database
- [ ] Unit test: conversation history is maintained across messages
- [ ] Integration test: AI responds with board modifications that are applied
- [ ] Integration test: AI responds with text-only answer when no board changes needed

**Success criteria:** AI can read the board, answer questions about it, and modify it via structured outputs. Changes persist in the database.

---

## Part 10: AI Chat Sidebar

Add a sidebar UI for AI chat that can update the board in real time.

- [ ] Create collapsible sidebar component (right side of board)
- [ ] Chat message list with user/AI message distinction
- [ ] Text input with send button
- [ ] Display AI responses with markdown rendering
- [ ] When AI returns board updates, apply them to the UI immediately
- [ ] Auto-scroll to latest message
- [ ] Loading indicator while AI is responding
- [ ] Style sidebar using project color scheme
- [ ] Sidebar toggle button in board header

**Tests:**
- [ ] Frontend unit: sidebar renders and toggles open/closed
- [ ] Frontend unit: sending a message calls the chat API
- [ ] Frontend unit: AI response displays in message list
- [ ] Frontend unit: board updates from AI are reflected in the board
- [ ] Frontend unit: loading state shows while waiting for AI
- [ ] E2e test: open sidebar, send message, receive response
- [ ] E2e test: AI creates a card via chat, card appears on board
- [ ] E2e test: AI moves a card via chat, card moves on board
- [ ] E2e test: conversation history maintained across messages
- [ ] Maintain >=80% coverage across all code

**Success criteria:** Sidebar chat works end-to-end. AI can read and modify the board through conversation. UI updates reflect AI changes immediately. All tests pass.
