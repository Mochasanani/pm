"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCenter,
  type DragEndEvent,
  type DragOverEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { moveCard, type BoardData } from "@/lib/kanban";
import {
  fetchBoard,
  renameColumn as renameColumnApi,
  createCard as createCardApi,
  deleteCard as deleteCardApi,
  moveCardApi,
  logout,
} from "@/lib/api";

type KanbanBoardProps = {
  user: string;
  onLogout: () => void;
};

export const KanbanBoard = ({ user, onLogout }: KanbanBoardProps) => {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);

  const loadBoard = useCallback(async () => {
    try {
      const data = await fetchBoard();
      setBoard(data);
      setError(null);
    } catch {
      setError("Failed to load board");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadBoard();
  }, [loadBoard]);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  const cardsById = useMemo(() => board?.cards ?? {}, [board?.cards]);

  // Board state before drag started, used for rollback on API failure
  const [preDragBoard, setPreDragBoard] = useState<BoardData | null>(null);

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(event.active.id as string);
    setPreDragBoard(board);
  };

  const handleDragOver = (event: DragOverEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id || !board) return;

    const newColumns = moveCard(board.columns, active.id as string, over.id as string);
    setBoard({ ...board, columns: newColumns });
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);

    if (!over || !board) {
      // Cancelled -- rollback
      if (preDragBoard) setBoard(preDragBoard);
      setPreDragBoard(null);
      return;
    }

    // Apply final position if different from current
    if (active.id !== over.id) {
      const newColumns = moveCard(board.columns, active.id as string, over.id as string);
      setBoard({ ...board, columns: newColumns });
    }

    // Fire API call for wherever the card ended up
    const cardId = active.id as string;
    const targetCol = board.columns.find((col) => col.cardIds.includes(cardId));
    if (targetCol) {
      const position = targetCol.cardIds.indexOf(cardId);
      moveCardApi(cardId, targetCol.id, position).catch(() => {
        if (preDragBoard) setBoard(preDragBoard);
      });
    }
    setPreDragBoard(null);
  };

  const handleRenameColumn = (columnId: string, title: string) => {
    if (!board) return;
    setBoard({
      ...board,
      columns: board.columns.map((column) =>
        column.id === columnId ? { ...column, title } : column
      ),
    });
    renameColumnApi(columnId, title).catch(() => loadBoard());
  };

  const handleAddCard = async (columnId: string, title: string, details: string) => {
    try {
      const card = await createCardApi(columnId, title, details);
      const cardId = String(card.id);
      setBoard((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          cards: {
            ...prev.cards,
            [cardId]: { id: cardId, title: card.title, details: card.details },
          },
          columns: prev.columns.map((column) =>
            column.id === columnId
              ? { ...column, cardIds: [...column.cardIds, cardId] }
              : column
          ),
        };
      });
    } catch {
      loadBoard();
    }
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    if (!board) return;
    const prevBoard = board;
    setBoard({
      ...board,
      cards: Object.fromEntries(
        Object.entries(board.cards).filter(([id]) => id !== cardId)
      ),
      columns: board.columns.map((column) =>
        column.id === columnId
          ? { ...column, cardIds: column.cardIds.filter((id) => id !== cardId) }
          : column
      ),
    });
    deleteCardApi(cardId).catch(() => setBoard(prevBoard));
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
          Loading board...
        </p>
      </div>
    );
  }

  if (error || !board) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <p className="text-sm font-semibold text-red-600">{error ?? "Something went wrong"}</p>
          <button
            type="button"
            onClick={() => { setLoading(true); loadBoard(); }}
            className="mt-4 rounded-full bg-[var(--primary-blue)] px-6 py-2 text-sm font-semibold text-white"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const activeCard = activeCardId ? cardsById[activeCardId] : null;

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1500px] flex-col gap-10 px-6 pb-16 pt-12">
        <header className="flex flex-col gap-6 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Single Board Kanban
              </p>
              <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">
                Kanban Studio
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--gray-text)]">
                Keep momentum visible. Rename columns, drag cards between stages,
                and capture quick notes without getting buried in settings.
              </p>
            </div>
            <div className="flex items-start gap-4">
              <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-5 py-4">
                <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                  Focus
                </p>
                <p className="mt-2 text-lg font-semibold text-[var(--primary-blue)]">
                  One board. Five columns. Zero clutter.
                </p>
              </div>
              <div className="flex flex-col items-end gap-2 rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-5 py-4">
                <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                  {user}
                </p>
                <button
                  type="button"
                  onClick={async () => {
                    await logout();
                    onLogout();
                  }}
                  className="rounded-full border border-[var(--stroke)] px-4 py-1.5 text-xs font-semibold text-[var(--gray-text)] transition hover:border-[var(--navy-dark)] hover:text-[var(--navy-dark)]"
                >
                  Sign out
                </button>
              </div>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            {board.columns.map((column) => (
              <div
                key={column.id}
                className="flex items-center gap-2 rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]"
              >
                <span className="h-2 w-2 rounded-full bg-[var(--accent-yellow)]" />
                {column.title}
              </div>
            ))}
          </div>
        </header>

        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDragEnd={handleDragEnd}
        >
          <section className="grid gap-6 lg:grid-cols-5">
            {board.columns.map((column) => (
              <KanbanColumn
                key={column.id}
                column={column}
                cards={column.cardIds.map((cardId) => board.cards[cardId])}
                isDragTarget={activeCardId != null && column.cardIds.includes(activeCardId) && !preDragBoard?.columns.find((c) => c.id === column.id)?.cardIds.includes(activeCardId)}
                onRename={handleRenameColumn}
                onAddCard={handleAddCard}
                onDeleteCard={handleDeleteCard}
              />
            ))}
          </section>
          <DragOverlay>
            {activeCard ? (
              <div className="w-[260px]">
                <KanbanCardPreview card={activeCard} />
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      </main>
    </div>
  );
};
