import { play } from "../lib/sound";
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { Bot, Check, Database, Loader2, MessageSquarePlus, PanelLeft, Pencil, Search, Send, Trash2, UserRound } from "lucide-react";
import { Btn, ErrorNote, Loading, cx, inputCls } from "../components/app/ui";
import { useAuth } from "../context/AuthContext";
import { fmtAgo } from "../lib/format";
import { useResource } from "../lib/useResource";
import { errorMessage } from "../services/api";
import {
  askAssistant,
  deleteSession,
  getAssistantInfo,
  getSession,
  getSessions,
  renameSession,
  type ChatMessage,
  type ChatSession,
  type Retrieval,
} from "../services/assistant";

const LEAD: Record<string, string> = {
  user: "Ask about your own readings, flags, visits and health centre. Answers come only from your records.",
  phc_worker: "Ask about the citizens in your catchment, their flags, your visits and local trends.",
  admin: "Ask about accounts, worker applications, health centres and platform activity. Totals only, never anyone's readings.",
};

/** Shown while the answer is on its way, so the question does not appear to vanish. */
const pending = (content: string): ChatMessage => ({
  id: "pending",
  role: "user",
  content,
  created_at: new Date().toISOString(),
  was_refused: false,
  refusal_reason: null,
  generated_sql: null,
  retrieval: null,
  latency_ms: null,
});

export function Assistant() {
  const { user } = useAuth();
  const info = useResource((s) => getAssistantInfo(s), "info");
  const [sessions, setSessions] = useState<ChatSession[] | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loadingThread, setLoadingThread] = useState(false);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [renaming, setRenaming] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [drawer, setDrawer] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    getSessions()
      .then(setSessions)
      .catch((e) => {
        setSessions([]);
        setError(errorMessage(e));
      });
  }, []);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, sending]);

  useEffect(() => {
    const el = input.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [draft]);

  const active = sessions?.find((s) => s.id === activeId) ?? null;
  const shown = (sessions ?? []).filter((s) => s.title.toLowerCase().includes(search.trim().toLowerCase()));

  const open = async (id: string) => {
    setDrawer(false);
    if (id === activeId) return;
    setActiveId(id);
    setError(null);
    setLoadingThread(true);
    try {
      setMessages((await getSession(id)).messages);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setLoadingThread(false);
    }
  };

  const startNew = () => {
    setActiveId(null);
    setMessages([]);
    setError(null);
    setDrawer(false);
    input.current?.focus();
  };

  const send = async (text: string) => {
    const content = text.trim();
    if (!content || sending) return;
    setSending(true);
    setError(null);
    setDraft("");
    setMessages((m) => [...m, pending(content)]);
    try {
      const out = await askAssistant(content, activeId);
      play("message");
      setMessages((m) => [...m.filter((x) => x.id !== "pending"), out.question, out.answer]);
      setActiveId(out.session.id);
      setSessions((list) => [out.session, ...(list ?? []).filter((s) => s.id !== out.session.id)]);
    } catch (e) {
      setMessages((m) => m.filter((x) => x.id !== "pending"));
      setDraft(content);
      setError(errorMessage(e));
    } finally {
      setSending(false);
      input.current?.focus();
    }
  };

  const remove = async (id: string) => {
    try {
      await deleteSession(id);
      setSessions((list) => (list ?? []).filter((s) => s.id !== id));
      setConfirmDelete(null);
      if (id === activeId) startNew();
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  const rename = async (id: string, title: string) => {
    setRenaming(null);
    const clean = title.trim().slice(0, 120);
    const current = sessions?.find((s) => s.id === id);
    if (!clean || clean === current?.title) return;
    try {
      const saved = await renameSession(id, clean);
      setSessions((list) => (list ?? []).map((s) => (s.id === id ? saved : s)));
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    void send(draft);
  };
  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void send(draft);
    }
  };

  const engine = info.data?.engine === "gemini" ? `Gemini (${info.data.model})` : "built-in rules";

  const chatList = (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center justify-between gap-2 p-4 pb-3">
        <h2 className="text-xl text-ink">Chats</h2>
        <Btn tone="primary" onClick={startNew} className="min-h-10 px-4">
          <MessageSquarePlus size={16} aria-hidden="true" /> New chat
        </Btn>
      </div>
      <div className="px-4 pb-3">
        <label className="relative block">
          <span className="visually-hidden">Search chats</span>
          <Search size={16} className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-ink-muted" aria-hidden="true" />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search chats"
            className={cx(inputCls, "min-h-10 pl-9")}
          />
        </label>
      </div>
      <nav aria-label="Chats" className="min-h-0 flex-1 overflow-y-auto px-2 pb-4">
        {sessions === null ? (
          <Loading />
        ) : shown.length === 0 ? (
          <p className="px-2 py-6 text-center text-sm text-ink-soft">
            {sessions.length === 0 ? "Your chats will be saved here, each with its own name." : "No chats match that search."}
          </p>
        ) : (
          <ul className="flex flex-col gap-1">
            {shown.map((s) => {
              const isActive = s.id === activeId;
              if (renaming === s.id) {
                return (
                  <li key={s.id} className="px-1">
                    <RenameField initial={s.title} onSave={(title) => void rename(s.id, title)} onCancel={() => setRenaming(null)} />
                  </li>
                );
              }
              if (confirmDelete === s.id) {
                return (
                  <li key={s.id} className="flex flex-wrap items-center gap-2 rounded-2xl bg-danger-soft px-3 py-2 text-sm text-danger" role="group" aria-label={`Delete "${s.title}"?`}>
                    <span className="min-w-0 flex-1 truncate">Delete "{s.title}"?</span>
                    <Btn tone="danger" className="min-h-9 px-3" onClick={() => void remove(s.id)}>
                      Delete
                    </Btn>
                    <Btn tone="ghost" className="min-h-9 px-3" onClick={() => setConfirmDelete(null)}>
                      Keep
                    </Btn>
                  </li>
                );
              }
              return (
                <li key={s.id} className={cx("group flex items-center gap-1 rounded-2xl", isActive ? "bg-lime" : "hover:bg-surface")}>
                  <button
                    type="button"
                    onClick={() => void open(s.id)}
                    onDoubleClick={() => setRenaming(s.id)}
                    aria-current={isActive || undefined}
                    className="min-h-12 min-w-0 flex-1 px-3 py-2 text-left"
                  >
                    <span className={cx("block truncate text-sm font-medium", isActive ? "text-olive" : "text-ink")}>{s.title}</span>
                    <span className={cx("block text-xs", isActive ? "text-olive/80" : "text-ink-muted")}>{fmtAgo(s.updated_at)}</span>
                  </button>
                  <span className="flex opacity-100 transition-opacity lg:opacity-0 lg:group-focus-within:opacity-100 lg:group-hover:opacity-100">
                    <button
                      type="button"
                      onClick={() => setRenaming(s.id)}
                      className="grid h-9 w-9 place-items-center rounded-full text-ink-soft hover:bg-paper-raised hover:text-ink"
                      aria-label={`Rename "${s.title}"`}
                    >
                      <Pencil size={15} aria-hidden="true" />
                    </button>
                    <button
                      type="button"
                      onClick={() => setConfirmDelete(s.id)}
                      className="mr-1 grid h-9 w-9 place-items-center rounded-full text-ink-soft hover:bg-paper-raised hover:text-danger"
                      aria-label={`Delete "${s.title}"`}
                    >
                      <Trash2 size={15} aria-hidden="true" />
                    </button>
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </nav>
    </div>
  );

  return (
    <div className="flex h-[calc(100dvh-57px)] min-h-0 lg:h-dvh">
      <aside className="hidden w-80 shrink-0 border-r border-line bg-paper-raised lg:block">{chatList}</aside>

      {drawer && (
        <div className="fixed inset-0 z-50 bg-ink/40 lg:hidden" onClick={() => setDrawer(false)}>
          <aside
            role="dialog"
            aria-modal="true"
            aria-label="Chats"
            className="absolute inset-y-0 left-0 w-[86%] max-w-sm bg-paper-raised shadow-[var(--hn-shadow-lg)]"
            onClick={(e) => e.stopPropagation()}
          >
            {chatList}
          </aside>
        </div>
      )}

      <section aria-label="Chat" className="flex min-w-0 flex-1 flex-col bg-paper">
        <header className="flex items-center gap-3 border-b border-line bg-surface px-4 py-3 md:px-6">
          <button
            type="button"
            onClick={() => setDrawer(true)}
            className="inline-flex min-h-10 items-center gap-2 rounded-full border border-line px-3 text-sm text-ink lg:hidden"
            aria-label="Open chats"
          >
            <PanelLeft size={16} aria-hidden="true" /> Chats
          </button>
          <div className="min-w-0 flex-1">
            {active && renaming === `header:${active.id}` ? (
              <RenameField initial={active.title} onSave={(title) => void rename(active.id, title)} onCancel={() => setRenaming(null)} />
            ) : (
              <div className="flex items-center gap-2">
                <h1 className="truncate text-2xl text-ink">{active?.title ?? "New chat"}</h1>
                {active && (
                  <button
                    type="button"
                    onClick={() => setRenaming(`header:${active.id}`)}
                    className="grid h-9 w-9 shrink-0 place-items-center rounded-full text-ink-soft hover:bg-paper-raised hover:text-ink"
                    aria-label="Rename this chat"
                  >
                    <Pencil size={15} aria-hidden="true" />
                  </button>
                )}
              </div>
            )}
            <p className="truncate text-xs text-ink-muted">{LEAD[user?.role ?? "user"]}</p>
          </div>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-6 md:px-8" aria-live="polite">
          <div className="mx-auto max-w-3xl">
            {loadingThread ? (
              <Loading label="Loading conversation" />
            ) : messages.length === 0 ? (
              <Welcome suggestions={info.data?.suggestions ?? []} onPick={(q) => void send(q)} disabled={sending} />
            ) : (
              <ol className="flex flex-col gap-5">
                {messages.map((m) => (
                  <Bubble key={m.id} message={m} />
                ))}
                {sending && (
                  <li className="flex items-center gap-2 text-sm text-ink-soft">
                    <Bot size={18} aria-hidden="true" /> Looking through the records…
                  </li>
                )}
              </ol>
            )}
            <div ref={bottom} />
          </div>
        </div>

        <div className="border-t border-line bg-surface px-4 py-3 md:px-8">
          <div className="mx-auto max-w-3xl">
            {error && (
              <div className="mb-2">
                <ErrorNote message={error} />
              </div>
            )}
            <form onSubmit={onSubmit} className="flex items-end gap-2 rounded-3xl border border-line-strong/40 bg-surface p-2 focus-within:border-ink focus-within:ring-3 focus-within:ring-[rgb(var(--hn-focus))]">
              <label className="visually-hidden" htmlFor="assistant-input">
                Your question
              </label>
              <textarea
                id="assistant-input"
                ref={input}
                rows={1}
                maxLength={1000}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={onKeyDown}
                placeholder="Ask about your readings…"
                className="hn-bare-input max-h-40 min-h-10 flex-1 resize-none bg-transparent px-3 py-2 text-sm text-ink placeholder:text-ink-muted"
              />
              <button
                type="submit"
                disabled={!draft.trim() || sending}
                aria-label={sending ? "Sending" : "Send"}
                aria-busy={sending || undefined}
                className={cx(
                  "grid h-10 w-10 shrink-0 place-items-center rounded-full transition-[background-color,box-shadow] duration-300",
                  draft.trim() && !sending
                    ? "bg-ink text-paper hover:shadow-[0_0_32px_rgb(var(--hn-glow))]"
                    : "cursor-not-allowed bg-paper-raised text-ink-muted",
                )}
              >
                {sending ? <Loader2 size={16} className="animate-spin" aria-hidden="true" /> : <Send size={16} aria-hidden="true" />}
              </button>
            </form>
            <p className="mt-2 text-center text-xs text-ink-muted">
              Answered by {engine} from Health Nexus records only. Not medical advice. In an emergency call 108.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}

function RenameField({ initial, onSave, onCancel }: { initial: string; onSave: (title: string) => void; onCancel: () => void }) {
  const [value, setValue] = useState(initial);
  const finished = useRef(false);
  const finish = (save: boolean) => {
    if (finished.current) return;
    finished.current = true;
    if (save) onSave(value);
    else onCancel();
  };
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        finish(true);
      }}
      className="flex items-center gap-1"
    >
      <label className="visually-hidden" htmlFor="rename-chat">
        Chat name
      </label>
      <input
        id="rename-chat"
        autoFocus
        value={value}
        maxLength={120}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Escape") finish(false);
        }}
        onBlur={() => finish(true)}
        className={cx(inputCls, "min-h-10")}
      />
      <button type="submit" className="grid h-9 w-9 shrink-0 place-items-center rounded-full text-ink hover:bg-paper-raised" aria-label="Save name">
        <Check size={16} aria-hidden="true" />
      </button>
    </form>
  );
}

function Welcome({ suggestions, onPick, disabled }: { suggestions: string[]; onPick: (q: string) => void; disabled: boolean }) {
  return (
    <div className="flex flex-col items-center gap-4 py-8 text-center">
      <span className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-brand-soft text-brand">
        <Bot size={24} aria-hidden="true" />
      </span>
      <p className="max-w-md text-sm text-ink-soft">Ask in your own words. Here are a few to start with:</p>
      <div className="flex max-w-2xl flex-wrap justify-center gap-2">
        {suggestions.map((q) => (
          <button
            key={q}
            type="button"
            disabled={disabled}
            onClick={() => onPick(q)}
            className="min-h-11 rounded-full border border-line px-4 text-sm text-ink hover:border-brand hover:text-brand disabled:opacity-50"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}

function Bubble({ message: m }: { message: ChatMessage }) {
  const mine = m.role === "user";
  return (
    <li className={cx("flex gap-3", mine && "flex-row-reverse")}>
      <span
        className={cx(
          "inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          mine ? "bg-paper-raised text-ink-soft" : "bg-brand-soft text-brand",
        )}
        aria-hidden="true"
      >
        {mine ? <UserRound size={16} /> : <Bot size={16} />}
      </span>
      <div className={cx("min-w-0 max-w-[85%]", mine && "text-right")}>
        <span className="visually-hidden">{mine ? "You said:" : "Assistant:"}</span>
        <div
          className={cx(
            "inline-block whitespace-pre-wrap break-words rounded-2xl px-4 py-2.5 text-left text-sm",
            mine ? "bg-brand text-on-brand" : m.was_refused ? "border border-line bg-paper-raised text-ink" : "bg-paper-raised text-ink",
          )}
        >
          {m.content}
        </div>
        {!mine && m.retrieval && <Sources message={m} retrieval={m.retrieval} />}
      </div>
    </li>
  );
}

/** "How I found this": the query that ran and the rows the answer was built from. */
function Sources({ message: m, retrieval: r }: { message: ChatMessage; retrieval: Retrieval }) {
  const args = Object.entries(r.args)
    .filter(([, v]) => v !== null && v !== "")
    .map(([k, v]) => `${k.replace(/_/g, " ")}: ${String(v)}`)
    .join(", ");
  return (
    <details className="mt-1 text-xs text-ink-soft">
      <summary className="inline-flex min-h-8 cursor-pointer items-center gap-1 hover:text-ink">
        <Database size={12} aria-hidden="true" />
        From "{r.title}" · {r.row_count} row{r.row_count === 1 ? "" : "s"}
        {m.latency_ms != null && ` · ${(m.latency_ms / 1000).toFixed(1)} s`}
      </summary>
      <div className="mt-2 flex flex-col gap-2 rounded-2xl border border-line bg-surface p-3 text-left">
        {args && <p>Parameters: {args}</p>}
        <p>Answered by: {r.engine === "rules" ? "built-in rules" : r.engine}</p>
        {r.rows.length > 0 && (
          <div className="max-h-56 overflow-auto">
            <table className="w-full text-left">
              <thead>
                <tr>
                  {r.columns.map((c) => (
                    <th key={c} className="whitespace-nowrap border-b border-line px-2 py-1 font-medium">
                      {c.replace(/_/g, " ")}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {r.rows.map((row, i) => (
                  <tr key={i}>
                    {r.columns.map((c) => (
                      <td key={c} className="whitespace-nowrap border-b border-line px-2 py-1 align-top text-ink">
                        {cell(row[c])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {m.generated_sql && (
          <details>
            <summary className="cursor-pointer hover:text-ink">SQL that ran (read-only)</summary>
            <pre className="mt-1 overflow-x-auto rounded-xl bg-paper-raised p-2 font-mono text-[11px] leading-snug text-ink">{m.generated_sql}</pre>
          </details>
        )}
      </div>
    </details>
  );
}

function cell(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}T/.test(value)) return new Date(value).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" });
  return String(value);
}
