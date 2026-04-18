"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  closestCorners,
  pointerWithin,
  rectIntersection,
  useSensor,
  useSensors,
  type CollisionDetection,
  type DragEndEvent,
  type DragOverEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { AiSidebar } from "@/components/AiSidebar";
import { BoardSwitcher } from "@/components/BoardSwitcher";
import { CardEditModal } from "@/components/CardEditModal";
import { ProfileModal } from "@/components/ProfileModal";
import { LogoutIcon, UserIcon } from "@/components/Icons";
import { moveCard, moveCardAcrossColumns, type BoardData } from "@/lib/kanban";
import {
  listBoards,
  createBoard,
  renameBoard,
  deleteBoard,
  fetchBoardById,
  renameColumnOnBoard,
  createCardOnBoard,
  deleteCardOnBoard,
  updateCardOnBoard,
  moveCardOnBoard,
  setCardLabels,
  logout,
  type Board,
  type User,
} from "@/lib/api";

type KanbanBoardProps = {
  user: User;
  onUserUpdated: (user: User) => void;
  onLogout: () => void;
};

const LAST_BOARD_KEY = "kanban.lastBoardId";

const readLastBoardId = (): number | null => {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(LAST_BOARD_KEY);
  const value = raw ? Number(raw) : NaN;
  return Number.isFinite(value) ? value : null;
};

const writeLastBoardId = (id: number) => {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(LAST_BOARD_KEY, String(id));
};

export const KanbanBoard = ({ user, onUserUpdated, onLogout }: KanbanBoardProps) => {
  const [profileOpen, setProfileOpen] = useState(false);
  const [boards, setBoards] = useState<Board[]>([]);
  const [currentBoardId, setCurrentBoardId] = useState<number | null>(null);
  const [board, setBoard] = useState<BoardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [editingCardId, setEditingCardId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterLabelIds, setFilterLabelIds] = useState<number[]>([]);

  const loadBoards = useCallback(async () => {
    try {
      const list = await listBoards();
      setBoards(list);
      setError(null);
      return list;
    } catch {
      setError("Failed to load boards");
      return [];
    }
  }, []);

  const loadBoardContent = useCallback(async (boardId: number) => {
    try {
      const data = await fetchBoardById(boardId);
      setBoard({ columns: data.columns, cards: data.cards, labels: data.labels ?? [] });
      setError(null);
    } catch {
      setError("Failed to load board");
    }
  }, []);

  // Initial load: boards list + pick a board + fetch its content.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const list = await loadBoards();
      if (cancelled || list.length === 0) {
        setLoading(false);
        return;
      }
      const lastId = readLastBoardId();
      const pick = list.find((b) => b.id === lastId) ?? list[0];
      setCurrentBoardId(pick.id);
      await loadBoardContent(pick.id);
      if (!cancelled) setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [loadBoards, loadBoardContent]);

  // Persist board selection and refetch content when switching.
  useEffect(() => {
    if (currentBoardId == null) return;
    writeLastBoardId(currentBoardId);
  }, [currentBoardId]);

  const handleSelectBoard = useCallback(
    async (boardId: number) => {
      if (boardId === currentBoardId) return;
      setCurrentBoardId(boardId);
      setBoard(null);
      setLoading(true);
      await loadBoardContent(boardId);
      setLoading(false);
    },
    [currentBoardId, loadBoardContent]
  );

  const handleCreateBoard = useCallback(
    async (name: string) => {
      const created = await createBoard(name);
      setBoards((prev) => [...prev, created]);
      await handleSelectBoard(created.id);
    },
    [handleSelectBoard]
  );

  const handleRenameBoard = useCallback(async (boardId: number, name: string) => {
    const updated = await renameBoard(boardId, { name });
    setBoards((prev) => prev.map((b) => (b.id === boardId ? updated : b)));
  }, []);

  const handleDeleteBoard = useCallback(
    async (boardId: number) => {
      await deleteBoard(boardId);
      const remaining = boards.filter((b) => b.id !== boardId);
      setBoards(remaining);
      if (boardId === currentBoardId && remaining.length > 0) {
        await handleSelectBoard(remaining[0].id);
      }
    },
    [boards, currentBoardId, handleSelectBoard]
  );

  // Invoked by AI sidebar after it mutates the board server-side.
  const refreshCurrentBoard = useCallback(async () => {
    if (currentBoardId == null) return;
    await loadBoardContent(currentBoardId);
  }, [currentBoardId, loadBoardContent]);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  // Prefer where the pointer is, then intersecting rects, then nearest corner.
  // Pure closestCenter picks distant targets in dense Kanban layouts — this
  // keeps the hovered column highlighted and inserts between cards correctly.
  const collisionDetection = useCallback<CollisionDetection>((args) => {
    const pointer = pointerWithin(args);
    if (pointer.length > 0) return pointer;
    const intersections = rectIntersection(args);
    if (intersections.length > 0) return intersections;
    return closestCorners(args);
  }, []);

  const cardsById = useMemo(() => board?.cards ?? {}, [board?.cards]);

  const [preDragBoard, setPreDragBoard] = useState<BoardData | null>(null);

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(event.active.id as string);
    setPreDragBoard(board);
  };

  const handleDragOver = (event: DragOverEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id || !board) return;

    const newColumns = moveCardAcrossColumns(board.columns, active.id as string, over.id as string);
    if (newColumns === board.columns) return;
    setBoard({ ...board, columns: newColumns });
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);

    if (!over || !board || currentBoardId == null) {
      if (preDragBoard) setBoard(preDragBoard);
      setPreDragBoard(null);
      return;
    }

    const cardId = active.id as string;
    const finalColumns =
      active.id !== over.id
        ? moveCard(board.columns, cardId, over.id as string)
        : board.columns;

    if (finalColumns !== board.columns) {
      setBoard({ ...board, columns: finalColumns });
    }

    const targetCol = finalColumns.find((col) => col.cardIds.includes(cardId));
    if (targetCol) {
      const position = targetCol.cardIds.indexOf(cardId);
      moveCardOnBoard(currentBoardId, cardId, targetCol.id, position).catch(() => {
        if (preDragBoard) setBoard(preDragBoard);
      });
    }
    setPreDragBoard(null);
  };

  const handleRenameColumn = (columnId: string, title: string) => {
    if (!board || currentBoardId == null) return;
    setBoard({
      ...board,
      columns: board.columns.map((column) =>
        column.id === columnId ? { ...column, title } : column
      ),
    });
    renameColumnOnBoard(currentBoardId, columnId, title).catch(() => refreshCurrentBoard());
  };

  const handleAddCard = async (columnId: string, title: string, details: string) => {
    if (currentBoardId == null) return;
    try {
      const card = await createCardOnBoard(currentBoardId, columnId, title, details);
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
      refreshCurrentBoard();
    }
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    if (!board || currentBoardId == null) return;
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
    deleteCardOnBoard(currentBoardId, cardId).catch(() => setBoard(prevBoard));
  };

  const handleUpdateCard = async (
    cardId: string,
    changes: {
      title: string;
      details: string;
      due_date: string | null;
      label_ids?: number[];
    }
  ) => {
    if (!board || currentBoardId == null) return;
    const prevBoard = board;
    const { label_ids, ...cardFields } = changes;
    setBoard({
      ...board,
      cards: {
        ...board.cards,
        [cardId]: {
          ...board.cards[cardId],
          ...cardFields,
          ...(label_ids !== undefined ? { label_ids } : {}),
        },
      },
    });
    try {
      await updateCardOnBoard(currentBoardId, cardId, cardFields);
      if (label_ids !== undefined) {
        const existing = [...(prevBoard.cards[cardId]?.label_ids ?? [])].sort();
        const next = [...label_ids].sort();
        const changed =
          existing.length !== next.length ||
          existing.some((v, i) => v !== next[i]);
        if (changed) {
          await setCardLabels(currentBoardId, cardId, label_ids);
        }
      }
    } catch (e) {
      setBoard(prevBoard);
      throw e;
    }
  };

  const handleDeleteCardById = (cardId: string) => {
    const column = board?.columns.find((col) => col.cardIds.includes(cardId));
    if (column) handleDeleteCard(column.id, cardId);
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
            onClick={() => {
              setLoading(true);
              loadBoards().then((list) => {
                const pick = list[0];
                if (pick) {
                  setCurrentBoardId(pick.id);
                  return loadBoardContent(pick.id).finally(() => setLoading(false));
                }
                setLoading(false);
              });
            }}
            className="mt-4 rounded-full bg-[var(--primary-blue)] px-6 py-2 text-sm font-semibold text-white"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const activeCard = activeCardId ? cardsById[activeCardId] : null;
  const totalCards = Object.keys(cardsById).length;

  const q = searchQuery.trim().toLowerCase();
  const cardMatches = (cardId: string): boolean => {
    const card = cardsById[cardId];
    if (!card) return false;
    if (q) {
      const hay = `${card.title} ${card.details}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    if (filterLabelIds.length > 0) {
      const ids = card.label_ids ?? [];
      if (!filterLabelIds.every((id) => ids.includes(id))) return false;
    }
    return true;
  };
  const filtering = q.length > 0 || filterLabelIds.length > 0;

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main
        className="relative flex min-h-screen flex-col gap-6 px-6 py-6 transition-[padding] duration-200"
        style={{ paddingRight: sidebarOpen ? "calc(380px + 1.5rem)" : "calc(48px + 1.5rem)" }}
      >
        <header className="flex items-center justify-between gap-4 rounded-2xl border border-[var(--stroke)] bg-white/80 px-6 py-4 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex items-center gap-4">
            <h1 className="font-display text-2xl font-semibold text-[var(--navy-dark)]">
              Kanban Studio
            </h1>
            <BoardSwitcher
              boards={boards}
              currentBoardId={currentBoardId}
              onSelect={handleSelectBoard}
              onCreate={handleCreateBoard}
              onRename={handleRenameBoard}
              onDelete={handleDeleteBoard}
            />
            <p className="hidden text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)] md:block">
              {board.columns.length} columns · {totalCards} cards
            </p>
            <input
              type="search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search cards"
              aria-label="Search cards"
              data-testid="card-search"
              className="hidden w-48 rounded-full border border-[var(--stroke)] bg-white px-3 py-1.5 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)] md:block"
            />
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setProfileOpen(true)}
              aria-label="Edit profile"
              title="Edit profile"
              className="hidden items-center gap-2 rounded-full border border-[var(--stroke)] bg-white px-3 py-1.5 text-sm font-medium text-[var(--navy-dark)] transition hover:border-[var(--navy-dark)] sm:flex"
            >
              <UserIcon width={14} height={14} />
              {user.display_name || user.username}
            </button>
            <button
              type="button"
              onClick={async () => {
                await logout();
                onLogout();
              }}
              aria-label="Sign out"
              title="Sign out"
              className="flex h-9 w-9 items-center justify-center rounded-full border border-[var(--stroke)] text-[var(--gray-text)] transition hover:border-[var(--navy-dark)] hover:text-[var(--navy-dark)]"
            >
              <LogoutIcon />
            </button>
          </div>
        </header>

        {(board.labels?.length ?? 0) > 0 && (
          <div
            data-testid="label-filter"
            className="flex flex-wrap items-center gap-2 rounded-2xl border border-[var(--stroke)] bg-white/60 px-4 py-2"
          >
            <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
              Filter by label
            </span>
            {(board.labels ?? []).map((label) => {
              const active = filterLabelIds.includes(label.id);
              return (
                <button
                  key={label.id}
                  type="button"
                  onClick={() =>
                    setFilterLabelIds((prev) =>
                      prev.includes(label.id)
                        ? prev.filter((id) => id !== label.id)
                        : [...prev, label.id]
                    )
                  }
                  aria-pressed={active}
                  data-testid={`filter-label-${label.id}`}
                  className="inline-flex items-center gap-1 rounded-full border px-3 py-0.5 text-xs font-semibold"
                  style={{
                    backgroundColor: active ? label.color : "transparent",
                    color: active ? "#ffffff" : label.color,
                    borderColor: label.color,
                  }}
                >
                  {label.name}
                </button>
              );
            })}
            {filterLabelIds.length > 0 && (
              <button
                type="button"
                onClick={() => setFilterLabelIds([])}
                className="text-[11px] font-semibold text-[var(--gray-text)] underline hover:text-[var(--navy-dark)]"
              >
                Clear
              </button>
            )}
          </div>
        )}

        <DndContext
          sensors={sensors}
          collisionDetection={collisionDetection}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDragEnd={handleDragEnd}
        >
          <section className="grid flex-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
            {board.columns.map((column) => {
              const wasOriginalColumn =
                preDragBoard?.columns
                  .find((c) => c.id === column.id)
                  ?.cardIds.includes(activeCardId ?? "") ?? false;
              const isDragTarget =
                activeCardId != null &&
                column.cardIds.includes(activeCardId) &&
                !wasOriginalColumn;
              return (
                <KanbanColumn
                  key={column.id}
                  column={
                    filtering
                      ? { ...column, cardIds: column.cardIds.filter(cardMatches) }
                      : column
                  }
                  cards={
                    filtering
                      ? column.cardIds.filter(cardMatches).map((cardId) => board.cards[cardId])
                      : column.cardIds.map((cardId) => board.cards[cardId])
                  }
                  labels={board.labels ?? []}
                  isDragTarget={isDragTarget}
                  onRename={handleRenameColumn}
                  onAddCard={handleAddCard}
                  onDeleteCard={handleDeleteCard}
                  onOpenCard={(cardId) => setEditingCardId(cardId)}
                />
              );
            })}
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
      <AiSidebar
        open={sidebarOpen}
        onToggle={() => setSidebarOpen((v) => !v)}
        onBoardChanged={refreshCurrentBoard}
        boardId={currentBoardId}
      />
      {editingCardId && board.cards[editingCardId] && (
        <CardEditModal
          card={board.cards[editingCardId]}
          labels={board.labels ?? []}
          onClose={() => setEditingCardId(null)}
          onSave={(changes) => handleUpdateCard(editingCardId, changes)}
          onDelete={() => handleDeleteCardById(editingCardId)}
        />
      )}
      {profileOpen && (
        <ProfileModal
          user={user}
          onClose={() => setProfileOpen(false)}
          onUpdated={(u) => onUserUpdated(u)}
        />
      )}
    </div>
  );
};
