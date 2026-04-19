"use client";

import { useState } from "react";
import { login, register, type User } from "@/lib/api";

type LoginPageProps = {
  onAuthenticated: (user: User) => void;
};

type Mode = "login" | "register";

export const LoginPage = ({ onAuthenticated }: LoginPageProps) => {
  const [mode, setMode] = useState<Mode>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const isRegister = mode === "register";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    const result = isRegister
      ? await register({
          username,
          password,
          display_name: displayName || undefined,
          email: email || undefined,
        })
      : await login(username, password);
    setLoading(false);
    if (result.ok) {
      onAuthenticated(result.user);
    } else {
      setError(result.error ?? (isRegister ? "Sign up failed" : "Login failed"));
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="relative">
        <div className="pointer-events-none absolute -left-40 -top-40 h-[320px] w-[320px] rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.2)_0%,_transparent_70%)]" />
        <div className="pointer-events-none absolute -bottom-32 -right-32 h-[280px] w-[280px] rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.15)_0%,_transparent_70%)]" />

        <form
          onSubmit={handleSubmit}
          className="relative w-[400px] rounded-[32px] border border-[var(--stroke)] bg-white/90 p-10 shadow-[var(--shadow)] backdrop-blur"
        >
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
            {isRegister ? "Create your account" : "Welcome back"}
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
                required
              />
            </div>
            {isRegister && (
              <>
                <div>
                  <label
                    htmlFor="displayName"
                    className="mb-1 block text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]"
                  >
                    Display name <span className="lowercase tracking-normal">(optional)</span>
                  </label>
                  <input
                    id="displayName"
                    type="text"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    className="w-full rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)] focus:ring-2 focus:ring-[var(--primary-blue)]/20"
                    autoComplete="name"
                  />
                </div>
                <div>
                  <label
                    htmlFor="email"
                    className="mb-1 block text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]"
                  >
                    Email <span className="lowercase tracking-normal">(optional)</span>
                  </label>
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)] focus:ring-2 focus:ring-[var(--primary-blue)]/20"
                    autoComplete="email"
                  />
                </div>
              </>
            )}
            <div>
              <label
                htmlFor="password"
                className="mb-1 block text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]"
              >
                Password {isRegister && <span className="lowercase tracking-normal">(min 8)</span>}
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)] focus:ring-2 focus:ring-[var(--primary-blue)]/20"
                autoComplete={isRegister ? "new-password" : "current-password"}
                minLength={isRegister ? 8 : undefined}
                required
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
            {loading
              ? isRegister
                ? "Creating account..."
                : "Signing in..."
              : isRegister
              ? "Create account"
              : "Sign in"}
          </button>

          <button
            type="button"
            onClick={() => {
              setError("");
              setMode(isRegister ? "login" : "register");
            }}
            className="mt-4 w-full text-center text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)] transition hover:text-[var(--navy-dark)]"
          >
            {isRegister
              ? "Already have an account? Sign in"
              : "Need an account? Sign up"}
          </button>
        </form>
      </div>
    </div>
  );
};
