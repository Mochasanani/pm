"use client";

import { useEffect, useState } from "react";
import { updateMe, type User } from "@/lib/api";

type ProfileModalProps = {
  user: User;
  onClose: () => void;
  onUpdated: (user: User) => void;
};

export const ProfileModal = ({ user, onClose, onUpdated }: ProfileModalProps) => {
  const [displayName, setDisplayName] = useState(user.display_name);
  const [email, setEmail] = useState(user.email ?? "");
  const [password, setPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const handleSave = async () => {
    setError(null);
    setSuccess(null);

    const changes: { display_name?: string; email?: string; password?: string } = {};
    const nextName = displayName.trim();
    if (nextName && nextName !== user.display_name) changes.display_name = nextName;
    const nextEmail = email.trim();
    if (nextEmail && nextEmail !== (user.email ?? "")) changes.email = nextEmail;
    if (password) {
      if (password.length < 8) {
        setError("Password must be at least 8 characters");
        return;
      }
      changes.password = password;
    }

    if (Object.keys(changes).length === 0) {
      setError("Nothing to save");
      return;
    }

    setSaving(true);
    try {
      const updated = await updateMe(changes);
      onUpdated(updated);
      setPassword("");
      setSuccess("Profile updated");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Edit profile"
      data-testid="profile-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-md rounded-2xl border border-[var(--stroke)] bg-white p-6 shadow-[var(--shadow)]">
        <div className="flex items-center justify-between pb-3">
          <h2 className="font-display text-lg font-semibold text-[var(--navy-dark)]">
            Your profile
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

        <p className="pb-3 text-xs text-[var(--gray-text)]">
          Signed in as <span className="font-semibold">{user.username}</span>
        </p>

        <label className="block pb-3 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
          Display name
          <input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className="mt-1 w-full rounded-lg border border-[var(--stroke)] px-3 py-2 text-sm font-normal normal-case tracking-normal text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
          />
        </label>

        <label className="block pb-3 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded-lg border border-[var(--stroke)] px-3 py-2 text-sm font-normal normal-case tracking-normal text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
          />
        </label>

        <label className="block pb-3 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
          New password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Leave blank to keep current"
            autoComplete="new-password"
            className="mt-1 w-full rounded-lg border border-[var(--stroke)] px-3 py-2 text-sm font-normal normal-case tracking-normal text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
          />
        </label>

        {error && (
          <p role="alert" className="pb-2 text-xs text-red-600">
            {error}
          </p>
        )}
        {success && (
          <p role="status" className="pb-2 text-xs text-emerald-600">
            {success}
          </p>
        )}

        <div className="flex items-center justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-[var(--stroke)] px-4 py-2 text-sm font-semibold text-[var(--gray-text)] hover:border-[var(--navy-dark)] hover:text-[var(--navy-dark)]"
          >
            Close
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
  );
};
