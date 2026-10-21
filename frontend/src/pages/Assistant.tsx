import { play } from "../lib/sound";
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import {
  ArrowRight,
  ArrowUp,
  Building2,
  Check,
  Database,
  Leaf,
  Loader2,
  MessageCircle,
  MessageSquareText,
  MoreVertical,
  PanelLeftClose,
  PanelLeftOpen,
  Pencil,
  Plus,
  Search,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Trash2,
  UserRound,
  Users,
} from "lucide-react";
import { ErrorNote, Loading, cx, inputCls } from "../components/app/ui";
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

/** Nira's mascot. Set this to the image path (e.g. "/brand/nira.png") once the artwork is in place. */
const NIRA_ART: string | null = null;

type Starter = { icon: typeof Users; title: string; body: string; ask: string | null };

const STARTERS: Record<string, Starter[]> = {
  user: [
    { icon: Users, title: "Explore your records", body: "Latest readings, averages over time and how often you log.", ask: "Show my latest readings" },
    { icon: Building2, title: "Healthcare access", body: "Your health centre, your next visit and recent examinations.", ask: "When is my next visit and which centre looks after me?" },
    { icon: ShieldAlert, title: "Understand a flag", body: "Which readings were flagged, why, and any advisories for your area.", ask: "Were any of my readings flagged this month?" },
    { icon: MessageSquareText, title: "Ask anything", body: "Clear answers in plain words, only from your HealthNexus records.", ask: null },
  ],
  phc_worker: [
    { icon: Users, title: "Explore your catchment", body: "Citizens, readings, flags and who has gone quiet.", ask: "Give me an overview of my catchment" },
    { icon: Building2, title: "Visits and schedule", body: "Visits booked in the coming days and ones waiting for an outcome.", ask: "What visits do I have in the next 3 days?" },
    { icon: ShieldAlert, title: "Investigate an issue", body: "Critical flags, symptoms going around and outbreak signals.", ask: "Who has critical flags right now?" },
    { icon: MessageSquareText, title: "Ask anything", body: "Clear, checked answers from your catchment's records.", ask: null },
  ],
  admin: [
    { icon: Users, title: "Explore platform records", body: "Ask about citizens, workers, applications and more.", ask: "Give me a platform overview" },
    { icon: Building2, title: "Healthcare access", body: "Find and understand centre information, staffing and load.", ask: "Which health centres have citizens but no worker?" },
    { icon: ShieldAlert, title: "Investigate an issue", body: "Understand flags, concerns, outbreak signals and pending actions.", ask: "Summarise the open support concerns" },
    { icon: MessageSquareText, title: "Ask anything", body: "Get clear, accurate answers from HealthNexus records.", ask: null },
  ],
};

const SCOPE: Record<string, string> = {
  user: "Searches your records",
  phc_worker: "Searches catchment records",
  admin: "Searches district records",
};

const TAGLINE = "Your AI companion for a healthier, more connected community.";

/** Shown while the answer is on its way, so the question does not appear to vanish. */
const pending = (content: string): ChatMessage => ({
  id: "pending",
  role: "user",
  content,
  created_at: new Date().toISOString(),
  was_refused: false,
  refusal_reason: null,
  retrieval: null,
  latency_ms: null,
});

function group(sessions: ChatSession[]): [string, ChatSession[]][] {
  const start = new Date();
  start.setHours(0, 0, 0, 0);
  const day = 86_400_000;
  const buckets: [string, ChatSession[]][] = [["Today", []], ["Yesterday", []], ["Previous 7 days", []], ["Older", []]];
  for (const s of sessions) {
    const t = new Date(s.updated_at).getTime();
    const i = t >= start.getTime() ? 0 : t >= start.getTime() - day ? 1 : t >= start.getTime() - 7 * day ? 2 : 3;
    buckets[i][1].push(s);
  }
  return buckets.filter(([, list]) => list.length);
}

export function Assistant() {
  const { user } = useAuth();
  const role = user?.role ?? "user";
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
  const [menu, setMenu] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [drawer, setDrawer] = useState(false);
  const [listOpen, setListOpen] = useState(true);
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

  useEffect(() => {
    if (!menu) return;
    const close = () => setMenu(null);
    window.addEventListener("click", close);
    return () => window.removeEventListener("click", close);
  }, [menu]);

  const active = sessions?.find((s) => s.id === activeId) ?? null;
  const shown = (sessions ?? []).filter((s) => s.title.toLowerCase().includes(search.trim().toLowerCase()));
  const empty = !loadingThread && messages.length === 0;

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

  const composer = (
    <form
      onSubmit={onSubmit}
      className="rounded-3xl border border-line bg-surface p-3 shadow-(--hn-shadow-md) focus-within:border-forest/50 focus-within:ring-3 focus-within:ring-forest/15"
    >
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
        placeholder="Ask Nira anything…"
        className="hn-bare-input block max-h-40 min-h-11 w-full resize-none bg-transparent px-2 py-2 text-base text-ink placeholder:text-ink-muted"
      />
      <div className="mt-1 flex items-center justify-between gap-2">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-paper px-3 py-1.5 text-xs font-medium text-ink-soft">
          <Database size={13} aria-hidden="true" /> {SCOPE[role]}
        </span>
        <button
          type="submit"
          disabled={!draft.trim() || sending}
          aria-label={sending ? "Sending" : "Send"}
          aria-busy={sending || undefined}
          className={cx(
            "grid h-11 w-11 shrink-0 place-items-center rounded-full transition-colors",
            draft.trim() && !sending ? "bg-forest text-white hover:bg-forest/90" : "cursor-not-allowed bg-paper-raised text-ink-muted",
          )}
        >
          {sending ? <Loader2 size={18} className="animate-spin" aria-hidden="true" /> : <ArrowUp size={18} aria-hidden="true" />}
        </button>
      </div>
    </form>
  );

  const chatList = (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center justify-between gap-2 px-5 pt-5 pb-4">
        <div className="flex items-center gap-2.5">
          <Leaf size={26} className="text-forest" aria-hidden="true" />
          <div>
            <p className="font-display text-2xl leading-none text-ink">Nira</p>
            <p className="mt-0.5 text-xs text-ink-soft">AI Health Assistant</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => (drawer ? setDrawer(false) : setListOpen(false))}
          className="grid h-9 w-9 place-items-center rounded-lg text-ink-soft hover:bg-paper hover:text-ink"
          aria-label="Hide chats"
        >
          <PanelLeftClose size={18} aria-hidden="true" />
        </button>
      </div>
      <div className="px-5">
        <button
          type="button"
          onClick={startNew}
          className="flex min-h-12 w-full items-center justify-center gap-2 rounded-full bg-forest text-sm font-semibold text-white shadow-sm transition-colors hover:bg-forest/90"
        >
          <Plus size={18} aria-hidden="true" /> New chat
        </button>
        <label className="relative mt-4 block">
          <span className="visually-hidden">Search chats</span>
          <Search size={16} className="pointer-events-none absolute top-1/2 left-4 -translate-y-1/2 text-ink-muted" aria-hidden="true" />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search chats"
            className={cx(inputCls, "min-h-11 border-transparent bg-surface pl-10")}
          />
        </label>
      </div>
      <nav aria-label="Chats" className="mt-4 min-h-0 flex-1 overflow-y-auto px-3 pb-4">
        {sessions === null ? (
          <Loading />
        ) : shown.length === 0 ? (
          <p className="px-2 py-6 text-center text-sm text-ink-soft">
            {sessions.length === 0 ? "Your chats will be saved here." : "No chats match that search."}
          </p>
        ) : (
          group(shown).map(([label, list]) => (
            <section key={label} className="mb-4">
              <h3 className="px-2 pb-1.5 text-xs font-semibold text-ink-soft">{label}</h3>
              <ul className="flex flex-col gap-0.5">
                {list.map((s) => {
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
                      <li key={s.id} className="flex flex-wrap items-center gap-2 rounded-xl bg-danger-soft px-3 py-2 text-sm text-danger" role="group" aria-label={`Delete "${s.title}"?`}>
                        <span className="min-w-0 flex-1 truncate">Delete "{s.title}"?</span>
                        <button type="button" className="rounded-full bg-danger px-3 py-1 text-xs font-semibold text-white" onClick={() => void remove(s.id)}>
                          Delete
                        </button>
                        <button type="button" className="rounded-full px-3 py-1 text-xs font-semibold text-ink-soft hover:bg-surface" onClick={() => setConfirmDelete(null)}>
                          Keep
                        </button>
                      </li>
                    );
                  }
                  return (
                    <li key={s.id} className={cx("group relative flex items-center rounded-xl", isActive ? "bg-matcha/30" : "hover:bg-surface/70")}>
                      <button
                        type="button"
                        onClick={() => void open(s.id)}
                        onDoubleClick={() => setRenaming(s.id)}
                        aria-current={isActive || undefined}
                        className="flex min-h-14 min-w-0 flex-1 items-start gap-3 px-3 py-2.5 text-left"
                      >
                        <MessageCircle size={18} className="mt-0.5 shrink-0 text-ink-soft" aria-hidden="true" />
                        <span className="min-w-0">
                          <span className="block truncate text-sm font-medium text-ink">{s.title}</span>
                          <span className="block text-xs text-ink-muted">{fmtAgo(s.updated_at)}</span>
                        </span>
                      </button>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setMenu(menu === s.id ? null : s.id);
                        }}
                        className={cx(
                          "mr-1 grid h-8 w-8 shrink-0 place-items-center rounded-lg text-ink-soft hover:bg-paper hover:text-ink",
                          isActive || menu === s.id ? "opacity-100" : "opacity-100 lg:opacity-0 lg:group-hover:opacity-100 lg:group-focus-within:opacity-100",
                        )}
                        aria-label={`Options for "${s.title}"`}
                        aria-expanded={menu === s.id}
                      >
                        <MoreVertical size={16} aria-hidden="true" />
                      </button>
                      {menu === s.id && (
                        <div role="menu" className="absolute top-11 right-2 z-20 w-36 overflow-hidden rounded-xl border border-line bg-surface py-1 shadow-(--hn-shadow-md)">
                          <button type="button" role="menuitem" onClick={() => setRenaming(s.id)} className="flex w-full items-center gap-2 px-3 py-2 text-sm text-ink hover:bg-paper">
                            <Pencil size={14} aria-hidden="true" /> Rename
                          </button>
                          <button type="button" role="menuitem" onClick={() => setConfirmDelete(s.id)} className="flex w-full items-center gap-2 px-3 py-2 text-sm text-red-700 hover:bg-red-50">
                            <Trash2 size={14} aria-hidden="true" /> Delete
                          </button>
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
            </section>
          ))
        )}
      </nav>
    </div>
  );

  return (
    <div className="flex h-[calc(100dvh-57px)] min-h-0 lg:h-[calc(100dvh-56px)]">
      {listOpen && <aside className="hidden w-80 shrink-0 border-r border-line bg-paper-raised/60 lg:block">{chatList}</aside>}

      {drawer && (
        <div className="fixed inset-0 z-50 bg-ink/40 lg:hidden" onClick={() => setDrawer(false)}>
          <aside
            role="dialog"
            aria-modal="true"
            aria-label="Chats"
            className="absolute inset-y-0 left-0 w-[86%] max-w-sm bg-paper shadow-(--hn-shadow-lg)"
            onClick={(e) => e.stopPropagation()}
          >
            {chatList}
          </aside>
        </div>
      )}

      <section aria-label="Chat" className="relative isolate flex min-w-0 flex-1 flex-col overflow-hidden bg-paper">
        <Decor />
        <header className="flex items-center gap-2 px-4 pt-3 md:px-6">
          <button
            type="button"
            onClick={() => setDrawer(true)}
            className="grid h-10 w-10 place-items-center rounded-lg text-ink-soft hover:bg-surface lg:hidden"
            aria-label="Open chats"
          >
            <PanelLeftOpen size={18} aria-hidden="true" />
          </button>
          {!listOpen && (
            <button
              type="button"
              onClick={() => setListOpen(true)}
              className="hidden h-10 w-10 place-items-center rounded-lg text-ink-soft hover:bg-surface lg:grid"
              aria-label="Show chats"
            >
              <PanelLeftOpen size={18} aria-hidden="true" />
            </button>
          )}
          {!empty && active && (
            <div className="min-w-0 flex-1">
              {renaming === `header:${active.id}` ? (
                <RenameField initial={active.title} onSave={(title) => void rename(active.id, title)} onCancel={() => setRenaming(null)} />
              ) : (
                <button type="button" onClick={() => setRenaming(`header:${active.id}`)} className="flex max-w-full items-center gap-2 rounded-lg px-2 py-1 text-left hover:bg-surface" title="Rename this chat">
                  <span className="truncate text-lg font-semibold text-ink">{active.title}</span>
                  <Pencil size={14} className="shrink-0 text-ink-muted" aria-hidden="true" />
                </button>
              )}
            </div>
          )}
        </header>

        {empty ? (
          <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 md:px-8">
            <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col items-center justify-center gap-8 py-8">
              <div className="flex flex-col items-center gap-3 text-center">
                {NIRA_ART && <img src={NIRA_ART} alt="" className="h-36 w-36 object-contain" />}
                <h1 className="font-display text-4xl text-ink md:text-5xl">
                  Hello, I’m <span className="text-forest">Nira.</span>
                </h1>
                <p className="text-base text-ink-soft">{TAGLINE}</p>
              </div>
              <div className="grid w-full gap-4 sm:grid-cols-2">
                {STARTERS[role].map((c) => (
                  <StarterCard key={c.title} starter={c} disabled={sending} onPick={() => (c.ask ? void send(c.ask) : input.current?.focus())} />
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="min-h-0 flex-1 overflow-y-auto px-4 py-6 md:px-8" aria-live="polite">
            <div className="mx-auto max-w-3xl">
              {loadingThread ? (
                <Loading label="Loading conversation" />
              ) : (
                <ol className="flex flex-col gap-5">
                  {messages.map((m) => (
                    <Bubble key={m.id} message={m} />
                  ))}
                  {sending && (
                    <li className="flex items-center gap-2 text-sm text-ink-soft">
                      <Sparkles size={18} className="animate-pulse text-forest" aria-hidden="true" /> Nira is looking through the records…
                    </li>
                  )}
                </ol>
              )}
              <div ref={bottom} />
            </div>
          </div>
        )}

        <div className="px-4 pt-2 pb-3 md:px-8">
          <div className="mx-auto max-w-3xl">
            {error && (
              <div className="mb-2">
                <ErrorNote message={error} />
              </div>
            )}
            {composer}
            <p className="mt-2.5 text-center text-xs text-ink-muted">
              Nira uses HealthNexus records only ({engine}). Not medical advice. In an emergency call 108.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}

/** Soft leaf shapes in the corners, behind everything. */
function Decor() {
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10">
      <div className="absolute -top-24 -right-24 h-72 w-72 rounded-full bg-matcha/15" />
      <div className="absolute top-28 -right-10 h-40 w-24 rotate-30 rounded-[100%_0] bg-matcha/35" />
      <div className="absolute -right-16 -bottom-20 h-56 w-56 rounded-full bg-matcha/15" />
    </div>
  );
}

function StarterCard({ starter: c, onPick, disabled }: { starter: Starter; onPick: () => void; disabled: boolean }) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onPick}
      className="group flex items-start gap-4 rounded-2xl border border-line bg-surface/80 p-5 text-left shadow-sm transition-[border-color,box-shadow] hover:border-matcha hover:shadow-(--hn-shadow-md) disabled:opacity-60"
    >
      <span className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-matcha/25 text-forest">
        <c.icon size={22} aria-hidden="true" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-center justify-between gap-2">
          <span className="font-display text-lg text-ink">{c.title}</span>
          <ArrowRight size={18} className="shrink-0 text-ink-soft transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
        </span>
        <span className="mt-1 block text-sm text-ink-soft">{c.body}</span>
      </span>
    </button>
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

function Bubble({ message: m }: { message: ChatMessage }) {
  const mine = m.role === "user";
  return (
    <li className={cx("flex gap-3", mine && "flex-row-reverse")}>
      <span
        className={cx("inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full", mine ? "bg-paper-raised text-ink-soft" : "bg-forest text-white")}
        aria-hidden="true"
      >
        {mine ? <UserRound size={16} /> : <Leaf size={16} />}
      </span>
      <div className={cx("min-w-0 max-w-[85%]", mine && "text-right")}>
        <span className="visually-hidden">{mine ? "You said:" : "Nira:"}</span>
        <div
          className={cx(
            "inline-block whitespace-pre-wrap break-words rounded-2xl px-4 py-2.5 text-left text-sm",
            mine ? "bg-forest text-white" : m.was_refused ? "border border-line bg-surface text-ink" : "border border-line/60 bg-surface text-ink shadow-sm",
          )}
        >
          {m.content}
        </div>
        {!mine && m.retrieval && <Sources message={m} retrieval={m.retrieval} />}
      </div>
    </li>
  );
}

/** "How I found this": every source, the period, whether the numbers were checked, and the rows. */
function Sources({ message: m, retrieval: r }: { message: ChatMessage; retrieval: Retrieval }) {
  const args = Object.entries(r.args)
    .filter(([, v]) => v !== null && v !== "")
    .map(([k, v]) => `${k.replace(/_/g, " ")}: ${String(v)}`)
    .join(", ");
  return (
    <details className="mt-1 text-xs text-ink-soft">
      <summary className="inline-flex min-h-8 cursor-pointer flex-wrap items-center gap-x-1.5 gap-y-0.5 hover:text-ink">
        <Database size={12} aria-hidden="true" />
        Based on: {(r.sources ?? [r]).map((s) => `${s.title}${period(s.args)} (${s.row_count} row${s.row_count === 1 ? "" : "s"})`).join(" · ")}
        {r.grounded === true && (
          <span className="inline-flex items-center gap-1 rounded-full bg-green-50 px-2 py-0.5 font-semibold text-green-800">
            <ShieldCheck size={12} aria-hidden="true" /> Numbers checked
          </span>
        )}
        {r.grounded === false && <span className="rounded-full bg-amber-50 px-2 py-0.5 font-semibold text-amber-800">Plain summary used</span>}
        {m.latency_ms != null && <span>· {(m.latency_ms / 1000).toFixed(1)} s</span>}
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

function period(args: Record<string, unknown>): string {
  const days = Number(args.days);
  if (!days) return "";
  return days === 1 ? ", last day" : days % 30 === 0 && days >= 30 ? `, last ${days / 30} month${days === 30 ? "" : "s"}` : `, last ${days} days`;
}
