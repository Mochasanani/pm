# Frontend: Kanban Studio

## Stack

- Next.js 16 (app router) with React 19
- Tailwind CSS v4 (via `@tailwindcss/postcss`)
- @dnd-kit for drag-and-drop (core + sortable)
- TypeScript 5

## Structure

### App (`src/app/`)

- `layout.tsx` -- root layout with Space Grotesk (display) and Manrope (body) fonts
- `page.tsx` -- renders `<KanbanBoard />`
- `globals.css` -- CSS variables for the color scheme, Tailwind import, base styles

### Components (`src/components/`)

- `KanbanBoard.tsx` -- top-level client component. Owns all board state via `useState<BoardData>`. Sets up `DndContext` with `PointerSensor` and `closestCorners` collision detection. Handles drag start/end, column rename, card add, and card delete.
- `KanbanColumn.tsx` -- renders a single column. Uses `useDroppable` for drop target. Contains a `SortableContext` for its cards and a `NewCardForm` at the bottom. Shows "Drop a card here" placeholder when empty.
- `KanbanCard.tsx` -- renders a single card. Uses `useSortable` for drag-and-drop. Has a "Remove" button.
- `KanbanCardPreview.tsx` -- lightweight card rendering used in `DragOverlay` (the ghost that follows the cursor during drag).
- `NewCardForm.tsx` -- toggle-to-open form with title (required) and details fields. Resets and closes on submit or cancel.

### Data Layer (`src/lib/`)

- `kanban.ts` -- types and pure functions:
  - Types: `Card { id, title, details }`, `Column { id, title, cardIds }`, `BoardData { columns, cards }`
  - `initialData` -- hardcoded demo board with 5 columns and 8 cards
  - `moveCard(columns, activeId, overId)` -- pure function handling all drag-and-drop reordering (same-column reorder, cross-column move, drop onto empty column)
  - `createId(prefix)` -- generates IDs like `card-abc123xyz`

## State Management

All state is client-side in `KanbanBoard` via React `useState`. `BoardData` stores columns (with ordered `cardIds` arrays) separately from a flat `cards` record keyed by ID. The `moveCard` function is pure and returns new column arrays without mutating.

## Testing

### Unit Tests (Vitest + Testing Library + jsdom)

Config: `vitest.config.ts`. Path alias `@` -> `src/`. Setup file imports `@testing-library/jest-dom`.

- `src/lib/kanban.test.ts` -- tests `moveCard`: same-column reorder, cross-column move, drop onto column
- `src/components/KanbanBoard.test.tsx` -- tests board rendering (5 columns), column rename, card add/remove

Current coverage: ~77% statements. Components with low coverage: `KanbanCardPreview` (8%), `page.tsx` and `layout.tsx` (0% -- config files and simple wrappers).

### E2e Tests (Playwright)

Config: `playwright.config.ts`. Runs against `http://127.0.0.1:3000`. Auto-starts dev server. Chromium only.

- `tests/kanban.spec.ts` -- board loads, add card, drag card between columns

## Color Scheme (CSS Variables)

| Variable | Value | Usage |
|---|---|---|
| `--accent-yellow` | `#ecad0a` | Accent lines, highlights |
| `--primary-blue` | `#209dd7` | Links, key sections |
| `--secondary-purple` | `#753991` | Submit buttons, important actions |
| `--navy-dark` | `#032147` | Main headings |
| `--gray-text` | `#888888` | Supporting text, labels |

## Key Patterns

- All components use Tailwind utility classes with CSS variable references (e.g., `text-[var(--navy-dark)]`)
- `data-testid` attributes on columns (`column-{id}`) and cards (`card-{id}`) for test targeting
- `DragOverlay` renders a separate `KanbanCardPreview` rather than moving the actual card DOM node
- Column titles are editable via a plain `<input>` with no save button (updates on change)
