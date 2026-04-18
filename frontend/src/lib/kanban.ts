export type Card = {
  id: string;
  title: string;
  details: string;
  due_date?: string | null;
  label_ids?: number[];
};

export type Column = {
  id: string;
  title: string;
  cardIds: string[];
};

export type Label = {
  id: number;
  name: string;
  color: string;
};

export type BoardData = {
  columns: Column[];
  cards: Record<string, Card>;
  labels?: Label[];
};

export const isColumnId = (columns: Column[], id: string): boolean =>
  columns.some((column) => column.id === id);

export const findCardColumnId = (
  columns: Column[],
  cardId: string
): string | undefined =>
  columns.find((column) => column.cardIds.includes(cardId))?.id;

const findColumnId = (columns: Column[], id: string): string | undefined => {
  if (isColumnId(columns, id)) return id;
  return findCardColumnId(columns, id);
};

/**
 * Cross-column move only. Used during `onDragOver` to hand the card over to
 * the target column's SortableContext. Returns the input reference unchanged
 * when the card is already in the target column (so no state update fires).
 *
 * Same-column reordering is intentionally NOT done here — that would oscillate
 * under pointer-based collision detection. Same-column reorder is committed
 * in `onDragEnd` via `moveCard`.
 */
export const moveCardAcrossColumns = (
  columns: Column[],
  activeId: string,
  overId: string
): Column[] => {
  const activeColumnId = findCardColumnId(columns, activeId);
  const overColumnId = isColumnId(columns, overId)
    ? overId
    : findCardColumnId(columns, overId);

  if (!activeColumnId || !overColumnId) return columns;
  if (activeColumnId === overColumnId) return columns;

  const activeColumn = columns.find((c) => c.id === activeColumnId);
  const overColumn = columns.find((c) => c.id === overColumnId);
  if (!activeColumn || !overColumn) return columns;

  const isOverColumn = overColumnId === overId;
  const overCardIndex = isOverColumn
    ? overColumn.cardIds.length
    : overColumn.cardIds.indexOf(overId);
  const insertIndex = overCardIndex === -1 ? overColumn.cardIds.length : overCardIndex;

  const nextActiveCardIds = activeColumn.cardIds.filter((id) => id !== activeId);
  const nextOverCardIds = [...overColumn.cardIds];
  nextOverCardIds.splice(insertIndex, 0, activeId);

  return columns.map((column) => {
    if (column.id === activeColumnId) {
      return { ...column, cardIds: nextActiveCardIds };
    }
    if (column.id === overColumnId) {
      return { ...column, cardIds: nextOverCardIds };
    }
    return column;
  });
};

/**
 * Move a card to the position implied by `overId`, which may be a column
 * (append to end) or another card (insert at that card's index). Handles
 * same-column reorder and cross-column. Used on `onDragEnd` to commit the
 * final position.
 */
export const moveCard = (
  columns: Column[],
  activeId: string,
  overId: string
): Column[] => {
  const activeColumnId = findColumnId(columns, activeId);
  const overColumnId = findColumnId(columns, overId);

  if (!activeColumnId || !overColumnId) return columns;

  const activeColumn = columns.find((column) => column.id === activeColumnId);
  const overColumn = columns.find((column) => column.id === overColumnId);
  if (!activeColumn || !overColumn) return columns;

  const isOverColumn = isColumnId(columns, overId);

  if (activeColumnId === overColumnId) {
    if (isOverColumn) {
      // Dropped on the column chrome/gap — keep existing position if already
      // the last card; otherwise move to the end.
      if (activeColumn.cardIds[activeColumn.cardIds.length - 1] === activeId) {
        return columns;
      }
      const nextCardIds = activeColumn.cardIds.filter((id) => id !== activeId);
      nextCardIds.push(activeId);
      return columns.map((column) =>
        column.id === activeColumnId
          ? { ...column, cardIds: nextCardIds }
          : column
      );
    }

    const oldIndex = activeColumn.cardIds.indexOf(activeId);
    const newIndex = activeColumn.cardIds.indexOf(overId);

    if (oldIndex === -1 || newIndex === -1 || oldIndex === newIndex) {
      return columns;
    }

    const nextCardIds = [...activeColumn.cardIds];
    nextCardIds.splice(oldIndex, 1);
    nextCardIds.splice(newIndex, 0, activeId);

    return columns.map((column) =>
      column.id === activeColumnId
        ? { ...column, cardIds: nextCardIds }
        : column
    );
  }

  const activeIndex = activeColumn.cardIds.indexOf(activeId);
  if (activeIndex === -1) {
    return columns;
  }

  const nextActiveCardIds = [...activeColumn.cardIds];
  nextActiveCardIds.splice(activeIndex, 1);

  const nextOverCardIds = [...overColumn.cardIds];
  if (isOverColumn) {
    nextOverCardIds.push(activeId);
  } else {
    const overIndex = overColumn.cardIds.indexOf(overId);
    const insertIndex = overIndex === -1 ? nextOverCardIds.length : overIndex;
    nextOverCardIds.splice(insertIndex, 0, activeId);
  }

  return columns.map((column) => {
    if (column.id === activeColumnId) {
      return { ...column, cardIds: nextActiveCardIds };
    }
    if (column.id === overColumnId) {
      return { ...column, cardIds: nextOverCardIds };
    }
    return column;
  });
};
