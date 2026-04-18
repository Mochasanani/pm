# Code Review — Kanban Studio

_Date: 2026-04-18_

Scope: full-codebase review of the Kanban Studio project (Next.js frontend, FastAPI backend, Docker packaging). Findings cite `file:line` where applicable. Priorities reflect the project's "keep it simple, no over-engineering, no unnecessary defensive programming" ethos from `CLAUDE.md`.

---

## 1. Architecture & Design

**Strengths**
- Clean separation between `frontend/` (Next.js) and `backend/` (FastAPI). Backend serves the built frontend at `/` and the API under `/api/`, which keeps deployment to a single container.
- DB schema is simple and normalized (`users → columns → cards`) with cascading deletes and foreign keys enforced (`backend/app/db.py`).
- Services layer (`backend/app/services.py`) cleanly separates business logic from HTTP routing.
- Optimistic UI with rollback in `KanbanBoard.tsx` (around L101–106) — correct pattern for drag-and-drop.

**Issues**

1. **In-memory session storage is not durable** — `backend/app/auth.py:16` keeps sessions in a module-level dict. Every server restart logs every user out. No expiration. For a dockerized app that restarts on redeploy, this is a user-visible defect rather than pure tech debt.
2. **No API versioning** — frontend hard-codes paths (`frontend/src/lib/api.ts`). Fine for an MVP, but worth noting before the API is consumed by anything else.
3. **AI integration embeds full board state every request** — `backend/app/ai.py` passes the whole serialized board into the prompt. Scales poorly once boards are large, and every AI message re-fetches and re-serializes. No caching.
4. **AI model hardcoded** — `openai/gpt-oss-120b` is pinned in `ai.py`. Should be env-configurable.

---

## 2. Backend (FastAPI / Python)

**Strengths**
- Type hints throughout.
- Pydantic validates title/details length.
- `Depends(...)` used correctly for DB connection and auth.
- SQLite runs in WAL mode with foreign keys on — good defaults.
- Parameterised queries used consistently (see below for one style nit that is NOT a vulnerability).

**Issues**

1. **Hardcoded dev credentials** — `auth.py:12-13` has `VALID_USERNAME = "user"` / `VALID_PASSWORD = "password"`. For an MVP this is defensible, but it should be overridable via environment variable so a deployed instance isn't trivially accessible.
2. **No transactional boundary in multi-statement operations** — `services.py:move_card` (L139–151) and `services.py:delete_card` (L109–114) issue several `UPDATE`/`DELETE` statements and call `conn.commit()` at the end. If the process dies between statements, card positions could end up inconsistent. SQLite's autocommit-per-statement + a late `commit()` actually means everything here is in one implicit transaction, so this is less severe than it looks, but wrapping with `with conn:` would make the intent explicit.
3. **Dynamic SQL via f-string in `update_card`** — `services.py:92` builds `UPDATE cards SET {', '.join(sets)} WHERE id = ?`. The interpolated fragments (`"title = ?"`, `"details = ?"`) are hardcoded literals, so this is **not** a SQL injection. It is, however, an unusual pattern that will confuse a future reader; the simpler fix is two explicit branches or always updating both columns.
4. **No rate limiting on `/api/login` or AI endpoints** — login is brute-forceable and AI calls cost real money per request.
5. **AI response reports attempted updates, not applied ones** — `ai.py` returns the raw `board_updates` even when some were rejected. The client can't tell which succeeded.
6. **Conversation history is in-memory** — same restart problem as sessions. If the UX implies persistence, this is a bug; if it's intentional session-scoped memory, it should be explicit.

---

## 3. Frontend (Next.js / React)

**Strengths**
- Strong typing on props and API responses.
- Component hierarchy is small and readable.
- `@dnd-kit` usage is idiomatic.
- Basic a11y: labels on inputs, `aria-label` on icon buttons.

**Issues**

1. **ID type thrash between string and number** — backend returns numeric IDs; frontend converts to strings (`api.ts` around L48–57, L69) and `kanban.ts` operates on strings. This conversion is scattered and fragile. Pick one representation at the API boundary and normalise once.
2. **Error paths don't always clear loading state** — `KanbanBoard.tsx` `fetchBoard` (L42–49) and `LoginPage.tsx` can leave `loading=true` if the catch branch doesn't reset it.
3. **`logout` rejection not handled** — `KanbanBoard.tsx` (around L230–232) calls `onLogout()` unconditionally even if the logout API rejected.
4. **`NewCardForm` doesn't mirror backend validation** — backend enforces `min_length=1`, `max_length=200`; frontend only truthy-checks (`NewCardForm.tsx:15`). User can paste a 300-char title and hit a 422 with no friendly message.
5. **`AiSidebar` error handling is coarse** — catch-all swallows everything and still triggers `onBoardChanged`, so the board refreshes even when nothing was applied.
6. **Markdown rendering of card details** — if details are ever rendered via a Markdown component (e.g., `AiSidebar` ~L141), ensure the renderer disables raw HTML. Low risk today (single authenticated user), but easy to get wrong later.

---

## 4. Code Quality

1. **Conversation capping is over-engineered** — `ai.py` appears to both enforce a turn limit and then delete old rows from history. Pick one (sliding window on insert is simplest).
2. **Magic numbers without context** — `PointerSensor` distance of 6 and the 260px drag overlay width in `KanbanBoard.tsx`. Minor — either drop a one-line comment or accept them as tuning constants.
3. **Inconsistent error detail strings** — `HTTPException(detail=...)` messages vary across routers; fine functionally, slightly annoying on the client.
4. **Simplifiable branch in `moveCard`** — `kanban.ts` has an `isOverColumn` branch for the same-column case that is unreachable given the earlier `activeColumnId === overColumnId` guard.

---

## 5. Testing

**Strengths**
- 25 backend tests + unit + e2e is a reasonable spread for a project of this size.
- Tests target behaviour, not implementation.
- Happy-path e2e coverage (login, add, move, delete) is in place.

**Gaps worth closing (pragmatically — not for the sake of a coverage number)**
1. **AI failure modes** — timeout, malformed JSON, partial-apply. Current tests mock `APIError` but don't cover real transient failures.
2. **Move edge cases** — moving into an empty column, moving to the same position, concurrent moves of the same card.
3. **Auth edge cases** — wrong password then right password in the same session; session replay after server restart (will currently fail — this is actually the bug in §2.1).
4. **E2E error paths** — login failure, network drop mid-drag.

Skip: don't write perf tests or exhaustive unit tests for `moveCard` unless a real bug surfaces.

---

## 6. Tooling / Infra

1. **`.env.example` would help** — `.env` is correctly gitignored (verified), but there is no example file so a new contributor has to guess the required variables.
2. **`DEV_MODE` env used as a conditional in `board.py`** — a single dev-mode flag tends to grow ugly. Not urgent, but worth splitting if it gains a second responsibility.
3. **Dockerfile installs `curl` purely for healthcheck** — minor image-size cost. Fine.
4. **No CI** — no GitHub Actions or equivalent running tests on push. First real regression will hurt.
5. **`DB_PATH` resolved at import time** in `db.py` — makes it harder to override in tests. Low priority since tests already use a fixture.

---

## 7. Security

Concrete, ranked:

1. **Default credentials in source** (`auth.py:12-13`) — `user` / `password`. Move to env vars; fail-fast if unset in production.
2. **No rate limiting on `/api/login`** — brute force is trivial given weak default credentials.
3. **No CSRF protection** — SameSite=Lax cookies mitigate common cases but not all. Low priority for single-user MVP; revisit if you add any cross-origin flows.
4. **Sequential integer IDs** — enumeration is possible but gated by auth, and the services layer consistently joins on `user_id`, so cross-tenant access looks correctly blocked. Keep the join pattern disciplined as you add endpoints.
5. **AI endpoint has no abuse protection** — authenticated, but a compromised account can burn OpenRouter credit quickly. Add a per-user rate limit.

**Not a finding:** `.env` is *not* tracked in git (verified via `git ls-files`). Earlier analysis suggested it was; it isn't.

**Not a finding:** `services.py:92` is *not* SQL injectable; the f-string only interpolates hardcoded literals. Style nit only.

---

## 8. Top Recommendations (prioritised)

1. **Persist sessions** (auth.py) — store in SQLite, add expiration. Otherwise every redeploy logs everyone out. _~1–2h._
2. **Move credentials to env vars** — `AUTH_USERNAME` / `AUTH_PASSWORD`, required in non-dev. _~30m._
3. **Rate-limit `/api/login` and the AI chat endpoint** — a simple in-process limiter (e.g. `slowapi`) is enough. _~1h._
4. **Normalise ID types at the API boundary** — one conversion point, not scattered. Prevents a class of off-by-one bugs. _~2h._
5. **Add `.env.example`** and document required variables. _~10m._
6. **Mirror backend validation in `NewCardForm`** (max length, inline error). _~30m._
7. **Tighten `AiSidebar` error handling** — distinguish applied vs attempted mutations; only refresh on success. _~1h._
8. **Make DB transactions explicit** via `with conn:` in multi-statement services. Cheap insurance. _~20m._
9. **Add CI** — run backend pytest, frontend unit + lint, and Playwright smoke on PR. _~2h._
10. **Collapse the unreachable branch** in `kanban.ts:moveCard` and drop the post-hoc conversation pruning in `ai.py`. Small simplifications. _~20m._

---

## Summary

Solid MVP. The structure, typing, and test discipline are all better than typical for a project this size, and the code mostly avoids over-engineering. The meaningful defects are operational: session and conversation state live in process memory, default credentials live in source, and there's no rate limiting on money-spending endpoints. Fix those four or five things and this is in good shape.
