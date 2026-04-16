export const API_BASE =
  typeof window !== "undefined" && window.location.origin !== "http://localhost:3000"
    ? ""
    : "http://localhost:8000";

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

// Auth
export async function login(username: string, password: string): Promise<{ ok: boolean; error?: string }> {
  const res = await jsonPost("/api/login", { username, password });
  if (!res.ok) return { ok: false, error: "Invalid credentials" };
  return { ok: true };
}

export async function logout(): Promise<void> {
  await apiFetch("/api/logout", { method: "POST" });
}

export async function getMe(): Promise<{ username: string } | null> {
  const res = await apiFetch("/api/me");
  if (!res.ok) return null;
  return res.json();
}

import type { BoardData } from "./kanban";

// Board API
export async function fetchBoard(): Promise<BoardData> {
  const res = await apiFetch("/api/board");
  if (!res.ok) throw new Error("Failed to fetch board");
  const data = await res.json();
  // Convert numeric IDs from backend to strings for frontend consistency
  const cards: BoardData["cards"] = {};
  for (const [id, card] of Object.entries(data.cards)) {
    const c = card as { id: number; title: string; details: string };
    cards[String(c.id)] = { id: String(c.id), title: c.title, details: c.details };
  }
  const columns = data.columns.map((col: { id: number; title: string; cardIds: number[] }) => ({
    id: String(col.id),
    title: col.title,
    cardIds: col.cardIds.map(String),
  }));
  return { columns, cards };
}

export async function renameColumn(columnId: string, title: string) {
  const res = await jsonPut(`/api/board/columns/${columnId}`, { title });
  if (!res.ok) throw new Error("Failed to rename column");
}

export async function createCard(columnId: string, title: string, details: string) {
  const res = await jsonPost("/api/board/cards", { column_id: Number(columnId), title, details });
  if (!res.ok) throw new Error("Failed to create card");
  return res.json() as Promise<{ id: number; title: string; details: string }>;
}

export async function deleteCard(cardId: string) {
  const res = await apiFetch(`/api/board/cards/${cardId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete card");
}

export async function moveCardApi(cardId: string, columnId: string, position: number) {
  const res = await jsonPut(`/api/board/cards/${cardId}/move`, { column_id: Number(columnId), position });
  if (!res.ok) throw new Error("Failed to move card");
}

export type ChatReply = {
  response: string;
  board_updates: Array<Record<string, unknown>>;
};

export async function sendChat(message: string): Promise<ChatReply> {
  const res = await jsonPost("/api/ai/chat", { message });
  if (!res.ok) throw new Error("Chat failed");
  return res.json();
}
