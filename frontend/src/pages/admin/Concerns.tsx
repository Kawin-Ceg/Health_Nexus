import { useEffect, useState, type ReactNode } from "react";
import { AlertTriangle, Building2, CalendarX, Clock, Mail, MapPin, Tag, UserRound, Watch, X } from "lucide-react";
import { useToast } from "../../components/app/Toaster";
import { Empty, ErrorNote, Labelled, Loading, PageHeader, SearchInput, cx, inputCls } from "../../components/app/ui";
import { fmtAgo, fmtDateTime } from "../../lib/format";
import { useDebounced } from "../../lib/useDebounced";
import { useResource } from "../../lib/useResource";
import { errorMessage } from "../../services/api";
import { getConcerns, updateConcern, type ConcernCategory, type ConcernItem, type ConcernStage, type ConcernStatus, type Evidence } from "../../services/admin";

export const CATEGORY: Record<ConcernCategory, string> = {
  device_issue: "Smartwatch not syncing",
  worker_no_show: "Health worker did not come",
  worker_conduct: "Health worker's behaviour",
  citizen_missed_visits: "Repeated missed visits",
  citizen_conduct: "Citizen's behaviour",
  incorrect_diagnosis_flag: "Flag looks wrong",
  data_misuse: "Misuse of data",
  access_request: "Access request",
  harassment: "Harassment",
  app_problem: "App not working",
  other: "Something else",
};

const RAISERS = [
  { id: "user" as const, label: "From citizens" },
  { id: "phc_worker" as const, label: "From PHC workers" },
];

const STAGES: { id: ConcernStage; label: string }[] = [
  { id: "not_reviewed", label: "Not reviewed" },
  { id: "in_progress", label: "In progress" },
  { id: "action_taken", label: "Action taken" },
];

const STATUS: Record<ConcernStatus, { label: string; cls: string }> = {
  open: { label: "Not reviewed", cls: "bg-amber-100 text-amber-900" },
  in_review: { label: "In progress", cls: "bg-sky-100 text-sky-900" },
  resolved: { label: "Action taken", cls: "bg-green-100 text-green-900" },
  rejected: { label: "Dismissed", cls: "bg-paper-raised text-ink-soft" },
};

function StatusPill({ status }: { status: ConcernStatus }) {
  return <span className={cx("inline-block rounded-full px-3 py-1 text-xs font-semibold", STATUS[status].cls)}>{STATUS[status].label}</span>;
}

export function Concerns() {
  const [raiser, setRaiser] = useState<"user" | "phc_worker">("user");
  const [stage, setStage] = useState<ConcernStage>("not_reviewed");
  const [search, setSearch] = useState("");
  const q = useDebounced(search);
  const [category, setCategory] = useState<ConcernCategory | "">("");
  const [days, setDays] = useState<number | "">("");
  const [openId, setOpenId] = useState<string | null>(null);

  const query = { raiser, stage, q, category, days };
  const list = useResource((s) => getConcerns(query, s), JSON.stringify(query));
  const d = list.data;
  const open = d?.items.find((c) => c.id === openId) ?? null;

  return (
    <div className="font-sans">
      <PageHeader title="Complaints" lead="Problems raised by citizens and PHC workers in your district, with what the app itself recorded as evidence." />

      <div role="tablist" aria-label="Raised by" className="mb-4 inline-flex rounded-full border border-line bg-surface p-1">
        {RAISERS.map((r) => (
          <button
            key={r.id}
            type="button"
            role="tab"
            aria-selected={raiser === r.id}
            onClick={() => { setRaiser(r.id); setCategory(""); }}
            className={cx("min-h-10 rounded-full px-5 text-sm font-semibold transition-colors", raiser === r.id ? "bg-ink text-paper" : "text-ink-soft hover:text-ink")}
          >
            {r.label}
          </button>
        ))}
      </div>

      <SearchInput value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search name, email, reference or text" aria-label="Search complaints" className="mb-4" />

      <div role="tablist" aria-label="Stage" className="mb-5 flex flex-wrap gap-2">
        {STAGES.map((s) => (
          <button
            key={s.id}
            type="button"
            role="tab"
            aria-selected={stage === s.id}
            onClick={() => setStage(s.id)}
            className={cx(
              "inline-flex min-h-10 items-center gap-2 rounded-full border px-4 text-sm font-medium",
              stage === s.id ? "border-ink bg-ink text-paper" : "border-line bg-surface text-ink hover:border-ink/40",
            )}
          >
            {s.label}
            {d && <span className="tabular-nums opacity-70">{d.counts[s.id]}</span>}
          </button>
        ))}
      </div>

      <div className="mb-5 flex flex-wrap gap-3">
        <select aria-label="Category" value={category} onChange={(e) => setCategory(e.target.value as ConcernCategory | "")} className={cx(inputCls, "w-auto!")}>
          <option value="">All kinds</option>
          {(raiser === "user"
            ? (["device_issue", "worker_no_show", "worker_conduct", "incorrect_diagnosis_flag", "data_misuse", "access_request", "harassment", "app_problem", "other"] as ConcernCategory[])
            : (["citizen_missed_visits", "citizen_conduct", "app_problem", "access_request", "other"] as ConcernCategory[])
          ).map((c) => (
            <option key={c} value={c}>{CATEGORY[c]}</option>
          ))}
        </select>
        <select aria-label="Raised" value={days} onChange={(e) => setDays(e.target.value ? Number(e.target.value) : "")} className={cx(inputCls, "w-auto!")}>
          <option value="">Any time</option>
          <option value={1}>Last 24 hours</option>
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
        </select>
        {(category || days) && (
          <button type="button" onClick={() => { setCategory(""); setDays(""); }} className="text-sm text-ink-soft underline underline-offset-4">
            Clear filters
          </button>
        )}
      </div>

      {list.error && <ErrorNote message={list.error} onRetry={list.reload} />}
      {!d ? (
        !list.error && <Loading />
      ) : d.items.length === 0 ? (
        <Empty title="No complaints here" />
      ) : (
        <ul className={cx("grid gap-5 md:grid-cols-2 2xl:grid-cols-3", list.loading && "opacity-60")}>
          {d.items.map((c) => (
            <li key={c.id}>
              <button
                type="button"
                onClick={() => setOpenId(c.id)}
                className="flex h-full w-full flex-col gap-4 rounded-lg border border-line bg-surface p-5 text-left text-sm transition-colors hover:border-ink/40 focus-visible:outline-2 focus-visible:outline-ink"
              >
                <span className="flex items-start gap-4">
                  <Initials name={c.raised_by} />
                  <span className="min-w-0 flex-1">
                    <span className="block text-base font-semibold leading-snug text-ink">{c.raised_by}</span>
                    <span className="mt-0.5 block break-words text-ink-muted">{c.raised_by_email}</span>
                  </span>
                  <span className="shrink-0 rounded-md border border-line px-2.5 py-1 font-mono text-xs font-semibold text-ink">{c.ticket_ref}</span>
                </span>
                <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2">
                  <dt className="text-ink-muted">Kind</dt>
                  <dd className="text-ink">{CATEGORY[c.category]}</dd>
                  {c.subject && (
                    <>
                      <dt className="text-ink-muted">About</dt>
                      <dd className="text-ink">{c.subject}</dd>
                    </>
                  )}
                  <dt className="text-ink-muted">Says</dt>
                  <dd className="line-clamp-2 text-ink">{c.description}</dd>
                </dl>
                {c.evidence?.kind === "missed_visits" && (
                  <span className="inline-flex w-fit items-center gap-1.5 rounded-full bg-red-50 px-3 py-1 text-xs font-semibold text-red-800">
                    <CalendarX size={13} aria-hidden="true" /> {c.evidence.unexplained} unexplained missed visits
                  </span>
                )}
                <span className="mt-auto flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
                  <span>
                    <span className="block text-xs text-ink-muted">Raised</span>
                    <span className="text-ink">{fmtAgo(c.created_at)}</span>
                  </span>
                  <span className="text-right">
                    <span className="block text-xs text-ink-muted">Status</span>
                    <StatusPill status={c.status} />
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {open && <Review complaint={open} onClose={() => setOpenId(null)} onChanged={list.reload} />}
    </div>
  );
}

function Initials({ name }: { name: string }) {
  const initials = name.split(/\s+/).map((p) => p[0]).slice(0, 2).join("").toUpperCase();
  return <span className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-paper-raised text-sm font-semibold text-ink-muted" aria-hidden="true">{initials}</span>;
}

function Row({ icon: Icon, label, value }: { icon: typeof Mail; label: string; value: ReactNode }) {
  return (
    <div className="flex min-w-0 gap-3">
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-line text-ink-soft">
        <Icon size={18} aria-hidden="true" />
      </span>
      <div className="min-w-0">
        <dt className="text-sm font-semibold text-ink">{label}</dt>
        <dd className="mt-0.5 break-words text-sm text-ink-soft">{value}</dd>
      </div>
    </div>
  );
}

function EvidenceBlock({ e }: { e: Evidence }) {
  if (e.kind === "device") {
    return (
      <div className="flex flex-col gap-2 text-sm">
        <p className="text-ink">Last smartwatch sync: <span className="font-semibold">{e.last_sync ?? "never"}</span></p>
        <p className="text-ink-soft">
          Readings in the last 7 days:{" "}
          {Object.entries(e.last_7_days ?? {}).map(([k, n]) => `${{ watch: "smartwatch", phc: "examinations", self: "typed in" }[k] ?? k} ${n}`).join(", ") || "none"}
        </p>
      </div>
    );
  }
  const visits = e.visits ?? [];
  return (
    <div className="flex flex-col gap-3 text-sm">
      {e.kind === "missed_visits" ? (
        <p className={cx("rounded-xl p-3", e.eligible ? "bg-red-50 text-red-900" : "bg-paper text-ink")}>
          <span className="font-semibold">{e.unexplained} unexplained</span> of {e.missed} missed visits in the last {e.window_days} days. A complaint needs {e.threshold};
          visits the citizen explained do not count.
        </p>
      ) : (
        <p className="rounded-xl bg-paper p-3 text-ink">
          {visits.length ? `${visits.length} booked visit${visits.length === 1 ? "" : "s"} passed with no outcome recorded by the worker.` : "No overdue visits were on record when this was raised."}
        </p>
      )}
      {visits.length > 0 && (
        <ul className="flex flex-col divide-y divide-line rounded-xl border border-line">
          {visits.map((v) => (
            <li key={v.at} className="flex flex-col gap-0.5 px-3 py-2">
              <span className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-semibold text-ink">{v.when}</span>
                {e.kind === "missed_visits" &&
                  (v.explanation ? (
                    <span className="rounded-full bg-green-50 px-2.5 py-0.5 text-xs font-semibold text-green-800">Explained</span>
                  ) : (
                    <span className="rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-semibold text-red-800">No reason given</span>
                  ))}
              </span>
              <span className="text-xs text-ink-soft">
                {[v.location, v.worker && `with ${v.worker}`, v.reason].filter(Boolean).join(" · ")}
              </span>
              {v.explanation && <span className="text-xs text-ink">Citizen said: "{v.explanation}"</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Review({ complaint: c, onClose, onChanged }: { complaint: ConcernItem; onClose: () => void; onChanged: () => void }) {
  const [note, setNote] = useState(c.admin_note ?? "");
  const [busy, setBusy] = useState<ConcernStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { notify } = useToast();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = overflow;
    };
  }, [onClose]);

  const move = async (status: ConcernStatus) => {
    setBusy(status);
    setError(null);
    try {
      await updateConcern(c.id, { status, admin_note: note });
      notify({ tone: "success", title: STATUS[status].label, body: c.ticket_ref });
      onChanged();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(null);
    }
  };
  const closing = note.trim().length >= 3;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-3 backdrop-blur-sm" onClick={onClose}>
      <article
        role="dialog"
        aria-modal="true"
        aria-labelledby="complaint-title"
        onClick={(e) => e.stopPropagation()}
        className="relative flex max-h-[calc(100dvh-1.5rem)] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-line bg-surface font-sans text-sm shadow-xl"
      >
        <button type="button" onClick={onClose} aria-label="Close" className="absolute top-3 right-3 z-10 grid h-9 w-9 place-items-center rounded-full bg-paper text-ink hover:bg-paper-raised">
          <X size={18} aria-hidden="true" />
        </button>
        <div className="grid shrink-0 gap-5 p-5 md:grid-cols-[180px_1fr] md:gap-6">
          <div className="flex flex-col items-center gap-2 text-center md:items-start md:border-r md:border-line md:pr-6 md:text-left">
            <span className="font-mono text-xs font-semibold text-ink-soft">{c.ticket_ref}</span>
            <p id="complaint-title" className="text-lg font-bold leading-snug text-ink">{CATEGORY[c.category]}</p>
            <StatusPill status={c.status} />
          </div>
          <dl className="grid content-center gap-x-6 gap-y-5 sm:grid-cols-2 lg:grid-cols-3">
            <Row icon={UserRound} label="Raised by" value={`${c.raised_by} (${c.raised_by_role === "phc_worker" ? "PHC worker" : "citizen"})`} />
            <Row icon={Mail} label="Email" value={c.raised_by_email} />
            <Row icon={MapPin} label="District" value={c.raised_by_district ?? "—"} />
            <Row icon={AlertTriangle} label="About" value={c.subject ? `${c.subject} (${c.subject_role === "phc_worker" ? "PHC worker" : "citizen"})` : "No one in particular"} />
            <Row icon={Clock} label="Raised on" value={fmtDateTime(c.created_at)} />
            <Row icon={Tag} label="Handled by" value={c.handled_by ?? "Not yet"} />
          </dl>
        </div>

        <div className="grid min-h-0 flex-1 border-t border-line md:grid-cols-2">
          <div className="min-h-0 overflow-y-auto px-5 py-4 md:border-r md:border-line">
            <h3 className="mb-2 text-base font-bold text-ink">What they said</h3>
            <p className="mb-5 whitespace-pre-line text-ink">{c.description}</p>
            <h3 className="mb-2 flex items-center gap-2 text-base font-bold text-ink">
              {c.evidence?.kind === "device" ? <Watch size={16} aria-hidden="true" /> : <Building2 size={16} aria-hidden="true" />} Evidence from the app
            </h3>
            {c.evidence ? <EvidenceBlock e={c.evidence} /> : <p className="text-ink-soft">Nothing attached for this kind of complaint.</p>}
          </div>
          <div className="min-h-0 overflow-y-auto px-5 py-4">
            <h3 className="mb-4 text-base font-bold text-ink">Decision</h3>
            <div className="flex flex-col gap-4">
              <Labelled label="Note" hint="Shown to the person who raised it. Required to mark action taken or dismiss.">
                <textarea rows={4} maxLength={2000} className={cx(inputCls, "py-2")} value={note} onChange={(e) => setNote(e.target.value)} />
              </Labelled>
              <div className="flex flex-wrap gap-3">
                {c.status === "open" && (
                  <button type="button" disabled={!!busy} onClick={() => void move("in_review")} className="inline-flex min-h-11 items-center rounded-full bg-sky-100 px-5 font-semibold text-sky-950 hover:bg-sky-200 disabled:opacity-50">
                    {busy === "in_review" ? "Saving…" : "Start review"}
                  </button>
                )}
                {c.status !== "resolved" && (
                  <button type="button" disabled={!closing || !!busy} onClick={() => void move("resolved")} className="inline-flex min-h-11 items-center rounded-full bg-green-200 px-5 font-semibold text-green-950 hover:bg-green-300 disabled:opacity-50">
                    {busy === "resolved" ? "Saving…" : "Action taken"}
                  </button>
                )}
                {c.status !== "rejected" && (
                  <button type="button" disabled={!closing || !!busy} onClick={() => void move("rejected")} className="inline-flex min-h-11 items-center rounded-full bg-red-200 px-5 font-semibold text-red-950 hover:bg-red-300 disabled:opacity-50">
                    {busy === "rejected" ? "Saving…" : "Dismiss"}
                  </button>
                )}
                {(c.status === "resolved" || c.status === "rejected") && (
                  <button type="button" disabled={!!busy} onClick={() => void move("in_review")} className="inline-flex min-h-11 items-center rounded-full border border-line px-5 font-semibold text-ink hover:bg-paper disabled:opacity-50">
                    Reopen
                  </button>
                )}
              </div>
              {c.resolved_at && <p className="text-ink-soft">Closed {fmtDateTime(c.resolved_at)}.</p>}
              {error && <ErrorNote message={error} />}
            </div>
          </div>
        </div>
      </article>
    </div>
  );
}
