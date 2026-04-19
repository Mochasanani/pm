export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

function apiFetch(path: string, init?: RequestInit) {
  return fetch(`${API_BASE}${path}`, { credentials: "include", ...init });
}

function jsonPost(path: string, body: unknown) {
  return apiFetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

function jsonPut(path: string, body: unknown) {
  return apiFetch(path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export type User = {
  id: number;
  username: string;
  email: string | null;
  display_name: string;
};

export type Board = {
  id: number;
  name: string;
  description: string;
  position: number;
  created_at: string;
  updated_at: string;
};

type AuthResult =
  | { ok: true; user: User }
  | { ok: false; error: string };

async function parseError(res: Response, fallback: string): Promise<string> {
  try {
    const data = await res.json();
    return (data.error as string) ?? (data.detail as string) ?? fallback;
  } catch {
    return fallback;
  }
}

// Auth
export async function login(username: string, password: string): Promise<AuthResult> {
  const res = await jsonPost("/api/login", { username, password });
  if (!res.ok) return { ok: false, error: await parseError(res, "Invalid credentials") };
  const user = (await res.json()) as User;
  return { ok: true, user };
}

export type RegisterInput = {
  username: string;
  password: string;
  display_name?: string;
  email?: string;
};

export async function register(input: RegisterInput): Promise<AuthResult> {
  const res = await jsonPost("/api/register", input);
  if (!res.ok) return { ok: false, error: await parseError(res, "Sign up failed") };
  const user = (await res.json()) as User;
  return { ok: true, user };
}

export async function logout(): Promise<void> {
  await apiFetch("/api/logout", { method: "POST" });
}

export async function getMe(): Promise<User | null> {
  const res = await apiFetch("/api/me");
  if (!res.ok) return null;
  return (await res.json()) as User;
}

export async function updateMe(input: {
  display_name?: string;
  email?: string;
  password?: string;
}): Promise<User> {
  const res = await jsonPut("/api/me", input);
  if (!res.ok) throw new Error(await parseError(res, "Failed to update profile"));
  return (await res.json()) as User;
}

// Boards (multi-board API)
export async function listBoards(): Promise<Board[]> {
  const res = await apiFetch("/api/boards");
  if (!res.ok) throw new Error("Failed to list boards");
  return (await res.json()) as Board[];
}

export async function createBoard(name: string, description = ""): Promise<Board> {
  const res = await jsonPost("/api/boards", { name, description });
  if (!res.ok) throw new Error(await parseError(res, "Failed to create board"));
  return (await res.json()) as Board;
}

export async function renameBoard(
  boardId: number,
  changes: { name?: string; description?: string }
): Promise<Board> {
  const res = await jsonPut(`/api/boards/${boardId}`, changes);
  if (!res.ok) throw new Error(await parseError(res, "Failed to rename board"));
  return (await res.json()) as Board;
}

export async function deleteBoard(boardId: number): Promise<void> {
  const res = await apiFetch(`/api/boards/${boardId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await parseError(res, "Failed to delete board"));
}

import type { BoardData, Label } from "./kanban";

type RawCard = {
  id: number;
  title: string;
  details: string;
  due_date?: string | null;
  label_ids?: number[];
};

function normalizeBoardContent(data: {
  cards: Record<string, RawCard>;
  columns: Array<{ id: number; title: string; cardIds: number[] }>;
  labels?: Label[];
}): BoardData {
  const cards: BoardData["cards"] = {};
  for (const card of Object.values(data.cards)) {
    cards[String(card.id)] = {
      id: String(card.id),
      title: card.title,
      details: card.details,
      due_date: card.due_date ?? null,
      label_ids: card.label_ids ?? [],
    };
  }
  const columns = data.columns.map((col) => ({
    id: String(col.id),
    title: col.title,
    cardIds: col.cardIds.map(String),
  }));
  return { columns, cards, labels: data.labels ?? [] };
}

// Board-scoped fetch. Returns board metadata alongside the board content.
export async function fetchBoardById(boardId: number): Promise<{ board: Board } & BoardData> {
  const res = await apiFetch(`/api/boards/${boardId}`);
  if (!res.ok) throw new Error("Failed to fetch board");
  const data = await res.json();
  return { board: data.board as Board, ...normalizeBoardContent(data) };
}

export async function renameColumnOnBoard(boardId: number, columnId: string, title: string) {
  const res = await jsonPut(`/api/boards/${boardId}/columns/${columnId}`, { title });
  if (!res.ok) throw new Error("Failed to rename column");
}

export async function createCardOnBoard(
  boardId: number,
  columnId: string,
  title: string,
  details: string,
  dueDate?: string | null
) {
  const body: Record<string, unknown> = {
    column_id: Number(columnId),
    title,
    details,
  };
  if (dueDate !== undefined) body.due_date = dueDate;
  const res = await jsonPost(`/api/boards/${boardId}/cards`, body);
  if (!res.ok) throw new Error("Failed to create card");
  return res.json() as Promise<RawCard>;
}

export async function deleteCardOnBoard(boardId: number, cardId: string) {
  const res = await apiFetch(`/api/boards/${boardId}/cards/${cardId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete card");
}

export async function updateCardOnBoard(
  boardId: number,
  cardId: string,
  changes: { title?: string; details?: string; due_date?: string | null }
) {
  const res = await jsonPut(`/api/boards/${boardId}/cards/${cardId}`, changes);
  if (!res.ok) throw new Error("Failed to update card");
  return res.json() as Promise<RawCard>;
}

export async function moveCardOnBoard(
  boardId: number,
  cardId: string,
  columnId: string,
  position: number
) {
  const res = await jsonPut(`/api/boards/${boardId}/cards/${cardId}/move`, {
    column_id: Number(columnId),
    position,
  });
  if (!res.ok) throw new Error("Failed to move card");
}

// Labels
export async function listLabels(boardId: number): Promise<Label[]> {
  const res = await apiFetch(`/api/boards/${boardId}/labels`);
  if (!res.ok) throw new Error("Failed to list labels");
  return (await res.json()) as Label[];
}

export async function createLabel(
  boardId: number,
  name: string,
  color = "#888888"
): Promise<Label> {
  const res = await jsonPost(`/api/boards/${boardId}/labels`, { name, color });
  if (!res.ok) throw new Error(await parseError(res, "Failed to create label"));
  return (await res.json()) as Label;
}

export async function updateLabel(
  boardId: number,
  labelId: number,
  changes: { name?: string; color?: string }
): Promise<Label> {
  const res = await jsonPut(`/api/boards/${boardId}/labels/${labelId}`, changes);
  if (!res.ok) throw new Error(await parseError(res, "Failed to update label"));
  return (await res.json()) as Label;
}

export async function deleteLabel(boardId: number, labelId: number): Promise<void> {
  const res = await apiFetch(`/api/boards/${boardId}/labels/${labelId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete label");
}

export async function setCardLabels(
  boardId: number,
  cardId: string,
  labelIds: number[]
): Promise<number[]> {
  const res = await jsonPut(
    `/api/boards/${boardId}/cards/${cardId}/labels`,
    { label_ids: labelIds }
  );
  if (!res.ok) throw new Error(await parseError(res, "Failed to set labels"));
  const body = (await res.json()) as { label_ids: number[] };
  return body.label_ids;
}

export type ChatReply = {
  response: string;
  board_updates: Array<Record<string, unknown>>;
  applied?: number;
  skipped?: number;
  board_id?: number;
};

export async function sendChat(message: string, boardId?: number): Promise<ChatReply> {
  const res = await jsonPost("/api/ai/chat", boardId != null ? { message, board_id: boardId } : { message });
  if (!res.ok) throw new Error("Chat failed");
  return res.json();
}

export async function clearConversation(boardId?: number): Promise<void> {
  const path = boardId != null ? `/api/ai/conversation?board_id=${boardId}` : "/api/ai/conversation";
  await apiFetch(path, { method: "DELETE" });
}
