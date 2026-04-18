import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import clsx from "clsx";
import type { Card, Label } from "@/lib/kanban";
import { TrashIcon } from "@/components/Icons";

const formatDueDate = (iso: string): string => {
  const [y, m, d] = iso.split("-").map(Number);
  if (!y || !m || !d) return iso;
  const date = new Date(y, m - 1, d);
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
};

const dueDateStatus = (iso: string): "overdue" | "soon" | "ok" => {
  const [y, m, d] = iso.split("-").map(Number);
  const due = new Date(y, m - 1, d);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diffDays = Math.round((due.getTime() - today.getTime()) / 86_400_000);
  if (diffDays < 0) return "overdue";
  if (diffDays <= 2) return "soon";
  return "ok";
};

type KanbanCardProps = {
  card: Card;
  labels?: Label[];
  onDelete: (cardId: string) => void;
  onOpen?: (cardId: string) => void;
};

export const KanbanCard = ({ card, labels = [], onDelete, onOpen }: KanbanCardProps) => {
  const cardLabels = (card.label_ids ?? [])
    .map((id) => labels.find((l) => l.id === id))
    .filter((x): x is Label => Boolean(x));
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: card.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <article
      ref={setNodeRef}
      style={style}
      className={clsx(
        "group relative rounded-2xl border border-transparent bg-white px-4 py-3 shadow-[0_8px_18px_rgba(3,33,71,0.06)]",
        "transition-all duration-150 hover:shadow-[0_12px_24px_rgba(3,33,71,0.1)]",
        isDragging && "opacity-0"
      )}
      {...attributes}
      {...listeners}
      data-testid={`card-${card.id}`}
    >
      <div className="flex items-start gap-2">
        <button
          type="button"
          onPointerDown={(e) => e.stopPropagation()}
          onClick={(e) => {
            e.stopPropagation();
            onOpen?.(card.id);
          }}
          aria-label={`Open ${card.title}`}
          className="min-w-0 flex-1 cursor-pointer text-left"
        >
          {cardLabels.length > 0 && (
            <div
              data-testid={`card-labels-${card.id}`}
              className="mb-1 flex flex-wrap gap-1"
            >
              {cardLabels.map((label) => (
                <span
                  key={label.id}
                  className="inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold text-white"
                  style={{ backgroundColor: label.color }}
                >
                  {label.name}
                </span>
              ))}
            </div>
          )}
          <h4 className="font-display text-sm font-semibold text-[var(--navy-dark)]">
            {card.title}
          </h4>
          {card.details && (
            <p className="mt-1 text-xs leading-5 text-[var(--gray-text)]">
              {card.details}
            </p>
          )}
          {card.due_date && (
            <span
              data-testid={`due-date-${card.id}`}
              data-status={dueDateStatus(card.due_date)}
              className={clsx(
                "mt-2 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold",
                dueDateStatus(card.due_date) === "overdue" &&
                  "bg-red-100 text-red-700",
                dueDateStatus(card.due_date) === "soon" &&
                  "bg-[var(--accent-yellow)]/20 text-[var(--accent-yellow)]",
                dueDateStatus(card.due_date) === "ok" &&
                  "bg-[var(--surface)] text-[var(--gray-text)]"
              )}
            >
              Due {formatDueDate(card.due_date)}
            </span>
          )}
        </button>
        <button
          type="button"
          onPointerDown={(e) => e.stopPropagation()}
          onClick={(e) => {
            e.stopPropagation();
            onDelete(card.id);
          }}
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[var(--gray-text)] opacity-0 transition hover:bg-red-50 hover:text-red-600 group-hover:opacity-100 focus:opacity-100 focus:outline-none focus:ring-2 focus:ring-red-200"
          aria-label={`Delete ${card.title}`}
        >
          <TrashIcon />
        </button>
      </div>
    </article>
  );
};
