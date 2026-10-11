import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { Bot, Database, MessageSquarePlus, Send, Trash2, UserRound } from "lucide-react";
import { Btn, ErrorNote, Loading, PageHeader, cx, inputCls } from "../components/app/ui";
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

  const open = async (id: string) => {
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
      if (id === activeId) startNew();
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

  return (
    <>
      <PageHeader
        title="Health assistant"
        lead={LEAD[user?.role ?? "user"]}
        actions={
          <Btn onClick={startNew}>
            <MessageSquarePlus size={16} aria-hidden="true" /> New chat
          </Btn>
        }
      />
      <div className="grid gap-4 lg:grid-cols-[240px_minmax(0,1fr)]">
        <nav aria-label="Conversations" className="order-2 lg:order-1">
          <h2 className="mb-2 text-xs font-medium uppercase tracking-wide text-ink-soft">Conversations</h2>
          {sessions === null ? (
            <Loading />
          ) : sessions.length === 0 ? (
            <p className="text-sm text-ink-soft">Your conversations will appear here.</p>
          ) : (
            <ul className="flex max-h-[60dvh] flex-col gap-1 overflow-y-auto">
              {sessions.map((s) => (
                <li key={s.id} className="group flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => void open(s.id)}
                    aria-current={s.id === activeId || undefined}
                    className={cx(
                      "min-h-11 min-w-0 flex-1 rounded-xl px-3 py-2 text-left text-sm",
                      s.id === activeId ? "bg-brand-soft text-brand" : "text-ink hover:bg-paper-raised",
                    )}
                  >
                    <span className="block truncate font-medium">{s.title}</span>
                    <span className="block text-xs text-ink-soft">{fmtAgo(s.updated_at)}</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => void remove(s.id)}
                    className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg text-ink-soft hover:bg-paper-raised hover:text-danger"
                    aria-label={`Delete "${s.title}"`}
                  >
                    <Trash2 size={16} aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </nav>

        <section aria-label="Chat" className="order-1 flex min-h-[60dvh] flex-col rounded-2xl border border-line bg-surface lg:order-2">
          <div className="flex-1 overflow-y-auto p-4" aria-live="polite">
            {loadingThread ? (
              <Loading label="Loading conversation" />
            ) : messages.length === 0 ? (
              <Welcome suggestions={info.data?.suggestions ?? []} onPick={(q) => void send(q)} disabled={sending} />
            ) : (
              <ol className="flex flex-col gap-4">
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
          {error && (
            <div className="px-4 pb-2">
              <ErrorNote message={error} />
            </div>
          )}
          <form onSubmit={onSubmit} className="flex items-end gap-2 border-t border-line p-3">
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
              placeholder="Ask a question…"
              className={cx(inputCls, "max-h-40 min-h-11 resize-y py-2.5")}
            />
            <Btn type="submit" tone="primary" busy={sending} disabled={!draft.trim()} aria-label="Send">
              <Send size={16} aria-hidden="true" />
            </Btn>
          </form>
          <p className="px-4 pb-3 text-xs text-ink-soft">
            Answered by {engine} from HealthNexus records only. Not medical advice. In an emergency call 108.
          </p>
        </section>
      </div>
    </>
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
      <div className="mt-2 flex flex-col gap-2 rounded-xl border border-line bg-surface p-3 text-left">
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
            <pre className="mt-1 overflow-x-auto rounded-lg bg-paper-raised p-2 font-mono text-[11px] leading-snug text-ink">{m.generated_sql}</pre>
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
