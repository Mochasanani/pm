"use client";

import { useState } from "react";
import { login } from "@/lib/api";

type LoginPageProps = {
  onLogin: () => void;
};

export const LoginPage = ({ onLogin }: LoginPageProps) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    const result = await login(username, password);
    setLoading(false);
    if (result.ok) {
      onLogin();
    } else {
      setError(result.error ?? "Login failed");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="relative">
        <div className="pointer-events-none absolute -left-40 -top-40 h-[320px] w-[320px] rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.2)_0%,_transparent_70%)]" />
        <div className="pointer-events-none absolute -bottom-32 -right-32 h-[280px] w-[280px] rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.15)_0%,_transparent_70%)]" />

        <form
          onSubmit={handleSubmit}
          className="relative w-[380px] rounded-[32px] border border-[var(--stroke)] bg-white/90 p-10 shadow-[var(--shadow)] backdrop-blur"
        >
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
            Welcome back
          </p>
          <h1 className="mt-3 font-display text-3xl font-semibold text-[var(--navy-dark)]">
            Kanban Studio
          </h1>

          <div className="mt-8 flex flex-col gap-4">
            <div>
              <label
                htmlFor="username"
                className="mb-1 block text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]"
              >
                Username
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)] focus:ring-2 focus:ring-[var(--primary-blue)]/20"
                autoComplete="username"
              />
            </div>
            <div>
              <label
                htmlFor="password"
                className="mb-1 block text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)] focus:ring-2 focus:ring-[var(--primary-blue)]/20"
                autoComplete="current-password"
              />
            </div>
          </div>

          {error && (
            <p className="mt-4 text-sm font-medium text-red-600" role="alert">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="mt-6 w-full rounded-full bg-[var(--primary-blue)] px-6 py-3 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-50"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
};
