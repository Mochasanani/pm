"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { clearConversation, sendChat } from "@/lib/api";
import {
  BroomIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  SendIcon,
  SparklesIcon,
} from "@/components/Icons";

type Message = { role: "user" | "assistant"; content: string };

type AiSidebarProps = {
  open: boolean;
  onToggle: () => void;
  onBoardChanged: () => void;
  boardId?: number | null;
};

export const AiSidebar = ({ open, onToggle, onBoardChanged, boardId }: AiSidebarProps) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setError(null);
    setMessages((m) => [...m, { role: "user", content: text }]);
    setLoading(true);
    try {
      const reply = await sendChat(text, boardId ?? undefined);
      const applied = reply.applied ?? reply.board_updates?.length ?? 0;
      const suffix = applied > 0 ? `\n\n_(${applied} change${applied === 1 ? "" : "s"} applied)_` : "";
      setMessages((m) => [
        ...m,
        { role: "assistant", content: reply.response + suffix },
      ]);
      setError(null);
      if (reply.board_updates && reply.board_updates.length > 0) {
        onBoardChanged();
      }
    } catch {
      setError("AI request failed");
    } finally {
      setLoading(false);
    }
  };

  const handleClear = async () => {
    setMessages([]);
    setError(null);
    try {
      await clearConversation(boardId ?? undefined);
    } catch {
      // best-effort
    }
  };

  if (!open) {
    return (
      <aside
        data-testid="ai-sidebar"
        data-state="collapsed"
        className="fixed right-0 top-0 z-40 flex h-screen w-12 flex-col items-center border-l border-[var(--stroke)] bg-white shadow-[var(--shadow)]"
      >
        <button
          type="button"
          onClick={onToggle}
          aria-label="Open chat"
          title="Open chat"
          className="mt-4 flex h-10 w-10 items-center justify-center rounded-full bg-[var(--secondary-purple)] text-white transition hover:brightness-110"
        >
          <SparklesIcon width={18} height={18} />
        </button>
        <span
          className="mt-4 text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]"
          style={{ writingMode: "vertical-rl" }}
        >
          Assistant
        </span>
        <button
          type="button"
          onClick={onToggle}
          aria-label="Expand chat"
          title="Expand chat"
          className="mt-auto mb-4 flex h-8 w-8 items-center justify-center rounded-full border border-[var(--stroke)] text-[var(--gray-text)] transition hover:text-[var(--navy-dark)]"
        >
          <ChevronLeftIcon />
        </button>
      </aside>
    );
  }

  return (
    <aside
      data-testid="ai-sidebar"
      data-state="expanded"
      className="fixed right-0 top-0 z-40 flex h-screen w-[380px] flex-col border-l border-[var(--stroke)] bg-white shadow-[var(--shadow)]"
    >
      <div className="flex items-center justify-between border-b border-[var(--stroke)] px-5 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--secondary-purple)] text-white">
            <SparklesIcon width={16} height={16} />
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
              Assistant
            </p>
            <h2 className="font-display text-base font-semibold text-[var(--navy-dark)]">
              Ask the AI
            </h2>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={handleClear}
            aria-label="Clear chat"
            title="Clear chat"
            className="flex h-8 w-8 items-center justify-center rounded-full text-[var(--gray-text)] transition hover:bg-[var(--surface)] hover:text-[var(--navy-dark)]"
          >
            <BroomIcon />
          </button>
          <button
            type="button"
            onClick={onToggle}
            aria-label="Collapse chat"
            title="Collapse chat"
            className="flex h-8 w-8 items-center justify-center rounded-full text-[var(--gray-text)] transition hover:bg-[var(--surface)] hover:text-[var(--navy-dark)]"
          >
            <ChevronRightIcon />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4" data-testid="ai-messages">
        {messages.length === 0 && !loading && (
          <p className="text-sm text-[var(--gray-text)]">
            Ask the assistant to create, move, edit, or delete cards.
          </p>
        )}
        <ul className="flex flex-col gap-3">
          {messages.map((m, i) => (
            <li
              key={i}
              data-testid={`ai-msg-${m.role}`}
              className={
                m.role === "user"
                  ? "self-end max-w-[85%] rounded-2xl bg-[var(--primary-blue)] px-4 py-2 text-sm text-white"
                  : "self-start max-w-[95%] rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-2 text-sm text-[var(--navy-dark)]"
              }
            >
              {m.role === "assistant" ? (
                <div className="prose prose-sm max-w-none">
                  <ReactMarkdown>{m.content}</ReactMarkdown>
                </div>
              ) : (
                m.content
              )}
            </li>
          ))}
          {loading && (
            <li
              data-testid="ai-loading"
              className="self-start rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-2 text-sm text-[var(--gray-text)]"
            >
              Thinking...
            </li>
          )}
        </ul>
        <div ref={endRef} />
      </div>

      {error && (
        <p className="border-t border-[var(--stroke)] px-5 py-2 text-xs text-red-600">{error}</p>
      )}

      <form
        className="flex items-center gap-2 border-t border-[var(--stroke)] px-5 py-4"
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
      >
        <input
          aria-label="Chat message"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask anything..."
          disabled={loading}
          className="flex-1 rounded-full border border-[var(--stroke)] bg-white px-4 py-2 text-sm outline-none focus:border-[var(--primary-blue)]"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          aria-label="Send"
          title="Send"
          className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--secondary-purple)] text-white transition hover:brightness-110 disabled:opacity-50"
        >
          <SendIcon width={16} height={16} />
        </button>
      </form>
    </aside>
  );
};
