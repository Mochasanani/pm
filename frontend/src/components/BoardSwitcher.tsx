"use client";

import { useEffect, useRef, useState } from "react";
import clsx from "clsx";
import type { Board } from "@/lib/api";
import { ChevronDownIcon, PlusIcon, PencilIcon, TrashIcon } from "@/components/Icons";

type BoardSwitcherProps = {
  boards: Board[];
  currentBoardId: number | null;
  onSelect: (boardId: number) => void;
  onCreate: (name: string) => Promise<void>;
  onRename: (boardId: number, name: string) => Promise<void>;
  onDelete: (boardId: number) => Promise<void>;
};

export const BoardSwitcher = ({
  boards,
  currentBoardId,
  onSelect,
  onCreate,
  onRename,
  onDelete,
}: BoardSwitcherProps) => {
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameDraft, setRenameDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
        setCreating(false);
        setRenamingId(null);
        setError(null);
      }
    };
    window.addEventListener("mousedown", handler);
    return () => window.removeEventListener("mousedown", handler);
  }, [open]);

  const current = boards.find((b) => b.id === currentBoardId) ?? boards[0] ?? null;

  const handleCreate = async () => {
    const name = newName.trim();
    if (!name) return;
    setBusy(true);
    setError(null);
    try {
      await onCreate(name);
      setNewName("");
      setCreating(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create");
    } finally {
      setBusy(false);
    }
  };

  const handleRename = async (boardId: number) => {
    const name = renameDraft.trim();
    if (!name) {
      setRenamingId(null);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await onRename(boardId, name);
      setRenamingId(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to rename");
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (boardId: number) => {
    if (boards.length <= 1) {
      setError("You must keep at least one board");
      return;
    }
    if (!confirm("Delete this board and all its cards?")) return;
    setBusy(true);
    setError(null);
    try {
      await onDelete(boardId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div ref={rootRef} className="relative" data-testid="board-switcher">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label="Switch board"
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex items-center gap-2 rounded-full border border-[var(--stroke)] bg-white px-4 py-1.5 text-sm font-semibold text-[var(--navy-dark)] transition hover:border-[var(--navy-dark)]"
      >
        <span className="max-w-[180px] truncate">{current?.name ?? "Select a board"}</span>
        <ChevronDownIcon
          className={clsx("transition", open && "rotate-180")}
          width={14}
          height={14}
        />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute left-0 top-full z-30 mt-2 w-72 rounded-2xl border border-[var(--stroke)] bg-white p-2 shadow-[var(--shadow)]"
        >
          <ul className="flex flex-col gap-1" data-testid="board-list">
            {boards.map((board) => {
              const isCurrent = board.id === current?.id;
              const isRenaming = renamingId === board.id;
              return (
                <li
                  key={board.id}
                  className={clsx(
                    "group flex items-center gap-1 rounded-lg px-2 py-1.5 text-sm",
                    isCurrent && "bg-[var(--surface)]"
                  )}
                >
                  {isRenaming ? (
                    <input
                      autoFocus
                      value={renameDraft}
                      onChange={(e) => setRenameDraft(e.target.value)}
                      onBlur={() => handleRename(board.id)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") e.currentTarget.blur();
                        if (e.key === "Escape") {
                          setRenamingId(null);
                        }
                      }}
                      aria-label="Rename board"
                      className="flex-1 rounded border border-[var(--stroke)] px-2 py-1 text-sm outline-none focus:border-[var(--primary-blue)]"
                    />
                  ) : (
                    <button
                      type="button"
                      onClick={() => {
                        onSelect(board.id);
                        setOpen(false);
                      }}
                      className={clsx(
                        "flex-1 truncate text-left font-medium",
                        isCurrent ? "text-[var(--navy-dark)]" : "text-[var(--gray-text)] hover:text-[var(--navy-dark)]"
                      )}
                    >
                      {board.name}
                    </button>
                  )}
                  {!isRenaming && (
                    <>
                      <button
                        type="button"
                        onClick={() => {
                          setRenameDraft(board.name);
                          setRenamingId(board.id);
                        }}
                        aria-label={`Rename ${board.name}`}
                        className="flex h-7 w-7 items-center justify-center rounded text-[var(--gray-text)] opacity-0 transition group-hover:opacity-100 hover:bg-[var(--surface-strong)] hover:text-[var(--navy-dark)]"
                      >
                        <PencilIcon width={14} height={14} />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(board.id)}
                        aria-label={`Delete ${board.name}`}
                        disabled={busy || boards.length <= 1}
                        className="flex h-7 w-7 items-center justify-center rounded text-[var(--gray-text)] opacity-0 transition group-hover:opacity-100 hover:bg-[var(--surface-strong)] hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-20"
                      >
                        <TrashIcon width={14} height={14} />
                      </button>
                    </>
                  )}
                </li>
              );
            })}
          </ul>

          <div className="mt-2 border-t border-[var(--stroke)] pt-2">
            {creating ? (
              <div className="flex items-center gap-1 px-1">
                <input
                  autoFocus
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleCreate();
                    }
                    if (e.key === "Escape") {
                      setCreating(false);
                      setNewName("");
                    }
                  }}
                  placeholder="Board name"
                  aria-label="New board name"
                  className="flex-1 rounded border border-[var(--stroke)] px-2 py-1 text-sm outline-none focus:border-[var(--primary-blue)]"
                />
                <button
                  type="button"
                  onClick={handleCreate}
                  disabled={busy || !newName.trim()}
                  className="rounded-full bg-[var(--primary-blue)] px-3 py-1 text-xs font-semibold text-white disabled:opacity-50"
                >
                  Add
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setCreating(true)}
                className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-sm font-semibold text-[var(--primary-blue)] hover:bg-[var(--surface)]"
              >
                <PlusIcon width={14} height={14} />
                New board
              </button>
            )}
          </div>

          {error && (
            <p role="alert" className="mt-2 px-2 text-xs text-red-600">
              {error}
            </p>
          )}
        </div>
      )}
    </div>
  );
};
