const API_BASE = typeof window !== "undefined" && window.location.origin !== "http://localhost:3000"
  ? ""
  : "http://localhost:8000";

export async function login(username: string, password: string): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(`${API_BASE}/api/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) return { ok: false, error: "Invalid credentials" };
  return { ok: true };
}

export async function logout(): Promise<void> {
  await fetch(`${API_BASE}/api/logout`, {
    method: "POST",
    credentials: "include",
  });
}

export async function getMe(): Promise<{ username: string } | null> {
  const res = await fetch(`${API_BASE}/api/me`, { credentials: "include" });
  if (!res.ok) return null;
  return res.json();
}
