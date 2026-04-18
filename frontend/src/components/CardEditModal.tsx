"use client";

import { useEffect, useState } from "react";
import type { Card, Label } from "@/lib/kanban";

type CardEditModalProps = {
  card: Card;
  labels?: Label[];
  onClose: () => void;
  onSave: (changes: {
    title: string;
    details: string;
    due_date: string | null;
    label_ids?: number[];
  }) => Promise<void> | void;
  onDelete?: () => void;
};

export const CardEditModal = ({ card, labels = [], onClose, onSave, onDelete }: CardEditModalProps) => {
  const [title, setTitle] = useState(card.title);
  const [details, setDetails] = useState(card.details);
  const [dueDate, setDueDate] = useState(card.due_date ?? "");
  const [selectedLabels, setSelectedLabels] = useState<number[]>(card.label_ids ?? []);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleLabel = (id: number) =>
    setSelectedLabels((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const handleSave = async () => {
    const trimmedTitle = title.trim();
    if (!trimmedTitle) {
      setError("Title is required");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onSave({
        title: trimmedTitle,
        details,
        due_date: dueDate ? dueDate : null,
        label_ids: selectedLabels,
      });
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Edit card"
      data-testid="card-edit-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-lg rounded-2xl border border-[var(--stroke)] bg-white p-6 shadow-[var(--shadow)]">
        <div className="flex items-center justify-between pb-3">
          <h2 className="font-display text-lg font-semibold text-[var(--navy-dark)]">
            Edit card
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded px-2 text-sm text-[var(--gray-text)] hover:text-[var(--navy-dark)]"
          >
            ×
          </button>
        </div>

        <label className="block pb-3 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
          Title
          <input
            autoFocus
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="mt-1 w-full rounded-lg border border-[var(--stroke)] px-3 py-2 text-sm font-normal normal-case tracking-normal text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
          />
        </label>

        <label className="block pb-3 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
          Details
          <textarea
            value={details}
            onChange={(e) => setDetails(e.target.value)}
            rows={5}
            className="mt-1 w-full rounded-lg border border-[var(--stroke)] px-3 py-2 text-sm font-normal normal-case tracking-normal text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
          />
        </label>

        <label className="block pb-3 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
          Due date
          <input
            type="date"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
            className="mt-1 w-full rounded-lg border border-[var(--stroke)] px-3 py-2 text-sm font-normal normal-case tracking-normal text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
          />
          {dueDate && (
            <button
              type="button"
              onClick={() => setDueDate("")}
              className="mt-1 text-[11px] font-semibold normal-case tracking-normal text-[var(--gray-text)] underline hover:text-[var(--navy-dark)]"
            >
              Clear due date
            </button>
          )}
        </label>

        {labels.length > 0 && (
          <div className="pb-3" data-testid="label-picker">
            <div className="pb-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
              Labels
            </div>
            <div className="flex flex-wrap gap-2">
              {labels.map((label) => {
                const active = selectedLabels.includes(label.id);
                return (
                  <button
                    key={label.id}
                    type="button"
                    onClick={() => toggleLabel(label.id)}
                    aria-pressed={active}
                    data-testid={`label-toggle-${label.id}`}
                    className="inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-semibold transition"
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
            </div>
          </div>
        )}

        {error && (
          <p role="alert" className="pb-2 text-xs text-red-600">
            {error}
          </p>
        )}

        <div className="flex items-center justify-between gap-3 pt-2">
          {onDelete ? (
            <button
              type="button"
              onClick={() => {
                if (confirm("Delete this card?")) {
                  onDelete();
                  onClose();
                }
              }}
              className="text-sm font-semibold text-red-600 hover:text-red-700"
            >
              Delete card
            </button>
          ) : (
            <span />
          )}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-full border border-[var(--stroke)] px-4 py-2 text-sm font-semibold text-[var(--gray-text)] hover:border-[var(--navy-dark)] hover:text-[var(--navy-dark)]"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="rounded-full bg-[var(--primary-blue)] px-5 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
