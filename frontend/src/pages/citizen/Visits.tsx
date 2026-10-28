import { useMemo, useState } from "react";
import { CalendarClock, Clock, MapPin, Phone, UserRound } from "lucide-react";
import { CUTOFF_HOURS, Detail, Mention, Modal, ProcessSteps, StatePill, VISIT_TYPE, changeable, type Step } from "../../components/app/visits";
import { useToast } from "../../components/app/Toaster";
import { Btn, ClearFilters, Empty, ErrorNote, Loading, PageHeader, SearchInput, cx, inputCls } from "../../components/app/ui";
import { fmtStamp } from "../../lib/format";
import { useResource } from "../../lib/useResource";
import { errorMessage } from "../../services/api";
import { cancelMyVisit, explainMissedVisit, getMySchedule, type Visit } from "../../services/health";

const TABS = [
  { id: "upcoming", label: "Upcoming", test: (v: Visit) => v.status === "scheduled" },
  { id: "done", label: "Done", test: (v: Visit) => v.status === "completed" },
  { id: "missed", label: "Missed", test: (v: Visit) => v.status === "missed" },
  { id: "cancelled", label: "Cancelled", test: (v: Visit) => v.status === "cancelled" },
] as const;
type Tab = (typeof TABS)[number]["id"];

const PERIODS = [
  { days: 0, label: "Any time" },
  { days: 7, label: "Within 7 days" },
  { days: 30, label: "Within 30 days" },
  { days: 90, label: "Within 3 months" },
];

const CANCEL_REASONS = ["I won't be at home", "I'm travelling that day", "I'm unwell and seeing a doctor", "I already had this check"];

export function CitizenVisits() {
  const res = useResource((s) => getMySchedule(s), "my-visits");
  const [tab, setTab] = useState<Tab>("upcoming");
  const [search, setSearch] = useState("");
  const [type, setType] = useState("");
  const [days, setDays] = useState(0);
  const [openId, setOpenId] = useState<string | null>(null);

  const visits = res.data ?? [];
  const counts = Object.fromEntries(TABS.map((t) => [t.id, visits.filter(t.test).length])) as Record<Tab, number>;
  const rows = useMemo(() => {
    const q = search.trim().toLowerCase();
    const test = TABS.find((t) => t.id === tab)!.test;
    return visits
      .filter(test)
      .filter((v) => !type || v.visit_type === type)
      .filter((v) => !days || Math.abs(new Date(v.scheduled_for).getTime() - Date.now()) <= days * 86400_000)
      .filter((v) => !q || `${v.reason ?? ""} ${v.location ?? ""} ${v.worker_name ?? ""} ${VISIT_TYPE[v.visit_type ?? "home"]}`.toLowerCase().includes(q))
      .sort((a, b) => (tab === "upcoming" ? a.scheduled_for.localeCompare(b.scheduled_for) : b.scheduled_for.localeCompare(a.scheduled_for)));
  }, [visits, tab, search, type, days]);
  const open = visits.find((v) => v.id === openId) ?? null;
  const filtered = !!(search || type || days);
  const clear = () => {
    setSearch("");
    setType("");
    setDays(0);
  };

  return (
    <>
      <PageHeader title="Visits" lead="Visits your health centre has booked with you." />
      <div className="mb-4 grid gap-3 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)_auto]">
        <SearchInput value={search} onChange={(e) => setSearch(e.target.value)} onClear={() => setSearch("")} placeholder="Search reason, place or health worker" aria-label="Search visits" />
        <div className="grid grid-cols-2 gap-3">
          <select aria-label="Kind of visit" value={type} onChange={(e) => setType(e.target.value)} className={cx(inputCls, "px-3")}>
            <option value="">All kinds</option>
            {Object.entries(VISIT_TYPE).map(([k, label]) => (
              <option key={k} value={k}>{label}</option>
            ))}
          </select>
          <select aria-label="When" value={days} onChange={(e) => setDays(Number(e.target.value))} className={cx(inputCls, "px-3")}>
            {PERIODS.map((p) => (
              <option key={p.days} value={p.days}>{p.label}</option>
            ))}
          </select>
        </div>
        <ClearFilters active={filtered} onClear={clear} />
      </div>
      <div role="tablist" aria-label="Status" className="mb-5 flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            className={cx("inline-flex min-h-10 items-center gap-2 rounded-xl border px-4 text-sm font-medium", tab === t.id ? "border-ink bg-ink text-paper" : "border-line bg-surface text-ink hover:border-ink/40")}
          >
            {t.label} <span className="tabular-nums opacity-70">{counts[t.id]}</span>
          </button>
        ))}
      </div>

      {res.error && <ErrorNote message={res.error} onRetry={res.reload} />}
      {!res.data ? (
        !res.error && <Loading />
      ) : rows.length === 0 ? (
        <Empty title={filtered ? "Nothing matches these filters" : tab === "upcoming" ? "No visits booked" : "Nothing here"} />
      ) : (
        <ul className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
          {rows.map((v) => (
            <li key={v.id}>
              <button
                type="button"
                onClick={() => setOpenId(v.id)}
                className="flex h-full w-full flex-col gap-4 rounded-lg border border-line bg-surface p-5 text-left text-sm transition-colors hover:border-ink/40 focus-visible:outline-2 focus-visible:outline-ink"
              >
                <span className="flex items-start gap-4">
                  <span className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-matcha/25 text-forest" aria-hidden="true">
                    <CalendarClock size={20} />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-base font-semibold leading-snug text-ink">{VISIT_TYPE[v.visit_type ?? "home"]}</span>
                    <span className="mt-0.5 block text-xs text-ink-muted">{v.duration_minutes ?? 30} min</span>
                  </span>
                  <StatePill visit={v} />
                </span>
                <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2">
                  <dt className="flex items-center gap-1.5 text-ink-muted"><Clock size={14} aria-hidden="true" /> When</dt>
                  <dd className="text-ink">{fmtStamp(v.scheduled_for)}</dd>
                  <dt className="flex items-center gap-1.5 text-ink-muted"><MapPin size={14} aria-hidden="true" /> Where</dt>
                  <dd className="text-ink">{v.location ?? "Your home"}</dd>
                  <dt className="flex items-center gap-1.5 text-ink-muted"><UserRound size={14} aria-hidden="true" /> With</dt>
                  <dd className="text-ink">{v.worker_name ?? "Your health centre"}</dd>
                </dl>
              </button>
            </li>
          ))}
        </ul>
      )}
      {open && <VisitDetails visit={open} onClose={() => setOpenId(null)} onChanged={res.reload} />}
    </>
  );
}

function stepsOf(v: Visit): Step[] {
  const worker = v.worker_name ?? "your health centre";
  const steps: Step[] = [
    {
      title: "Visit booked",
      state: "done",
      at: v.booked_at ? fmtStamp(v.booked_at) : undefined,
      detail: <>Booked by <Mention>{worker}</Mention></>,
    },
  ];
  if (v.status === "cancelled") {
    steps.push({
      title: "Visit cancelled",
      state: "failed",
      at: v.cancelled_at ? fmtStamp(v.cancelled_at) : undefined,
      detail: (
        <>
          Cancelled by {v.cancelled_by === "citizen" ? <Mention>you</Mention> : <Mention>{worker}</Mention>}
          {v.cancel_reason && <>: “{v.cancel_reason}”</>}
        </>
      ),
    });
    return steps;
  }
  const due = v.status === "scheduled";
  steps.push({
    title: v.status === "completed" ? "Health worker visited" : v.status === "missed" ? "Nobody was home" : "Visit",
    state: v.status === "completed" ? "done" : v.status === "missed" ? "failed" : v.state === "due_now" || v.state === "overdue" ? "current" : "todo",
    at: due ? (v.state === "due_now" ? "Happening now" : "Scheduled") : fmtStamp(v.scheduled_for),
    detail: due ? <>{fmtStamp(v.scheduled_for)} with <Mention>{worker}</Mention></> : <>With <Mention>{worker}</Mention></>,
  });
  if (due && steps[1].state === "todo") steps[1] = { ...steps[1], state: "current", at: "Waiting for the visit" };
  if (v.status === "missed") {
    steps.push({
      title: "Your reason",
      state: v.missed_reason ? "done" : "current",
      at: v.missed_reason_at ? fmtStamp(v.missed_reason_at) : "Waiting for you",
      detail: v.missed_reason ? `“${v.missed_reason}”` : "Tell your health centre why you missed it.",
    });
  }
  if (due || v.status === "completed") {
    steps.push({ title: "Follow-up", state: v.status === "completed" ? "done" : "todo", detail: "Your readings keep going to your health centre." });
  }
  return steps;
}

function VisitDetails({ visit: v, onClose, onChanged }: { visit: Visit; onClose: () => void; onChanged: () => void }) {
  const [cancelling, setCancelling] = useState(false);
  const { notify } = useToast();
  const canChange = changeable(v);

  return (
    <Modal title={VISIT_TYPE[v.visit_type ?? "home"]} onClose={onClose} wide>
      <div className="flex flex-col gap-5">
        <div className="flex flex-wrap items-center gap-3">
          <StatePill visit={v} />
          <span className="text-ink-soft">{fmtStamp(v.scheduled_for)}</span>
        </div>

        <ProcessSteps title="Visit status" steps={stepsOf(v)} />

        <dl className="grid gap-4 sm:grid-cols-2">
          <Detail label="Health worker">
            <span className="flex items-center gap-1.5"><UserRound size={14} aria-hidden="true" /> {v.worker_name ?? "Your health centre"}</span>
          </Detail>
          <Detail label="Contact">
            {v.worker_phone ? (
              <a href={`tel:${v.worker_phone.replace(/[^\d+]/g, "")}`} className="inline-flex items-center gap-1.5 text-ink underline underline-offset-4">
                <Phone size={14} aria-hidden="true" /> {v.worker_phone}
              </a>
            ) : (
              "Call your health centre"
            )}
          </Detail>
          <Detail label="Where"><span className="flex items-center gap-1.5"><MapPin size={14} aria-hidden="true" /> {v.location ?? "Your home"}</span></Detail>
          <Detail label="How long"><span className="flex items-center gap-1.5"><CalendarClock size={14} aria-hidden="true" /> About {v.duration_minutes ?? 30} minutes</span></Detail>
          {v.reason && <Detail label="Reason">{v.reason}</Detail>}
        </dl>

        {v.status === "missed" && !v.missed_reason && <MissedReason visit={v} onSaved={onChanged} />}

        {v.status === "scheduled" &&
          (canChange ? (
            cancelling ? (
              <QuickCancel
                onBack={() => setCancelling(false)}
                onCancel={async (reason) => {
                  await cancelMyVisit(v.id, reason);
                  notify({ tone: "success", title: "Visit cancelled", body: "Your health worker has been told." });
                  onChanged();
                  onClose();
                }}
              />
            ) : (
              <div>
                <Btn tone="danger" onClick={() => setCancelling(true)}>Cancel visit</Btn>
              </div>
            )
          ) : (
            <p className="rounded-xl bg-paper p-3 text-ink-soft">Less than {CUTOFF_HOURS} hours to go. Call your health worker to cancel.</p>
          ))}
      </div>
    </Modal>
  );
}

function QuickCancel({ onCancel, onBack }: { onCancel: (reason: string) => Promise<void>; onBack: () => void }) {
  const [picked, setPicked] = useState<string | null>(null);
  const [other, setOther] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const reason = picked === "other" ? other.trim() : picked;
  const ok = !!reason && reason.length >= 10;

  const send = async () => {
    if (!reason) return;
    setBusy(true);
    setError(null);
    try {
      await onCancel(reason);
    } catch (e) {
      setError(errorMessage(e));
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-line p-4">
      <p className="font-semibold text-ink">Why can't you make it?</p>
      <div className="flex flex-wrap gap-2">
        {[...CANCEL_REASONS, "other"].map((r) => (
          <button
            key={r}
            type="button"
            aria-pressed={picked === r}
            onClick={() => setPicked(r)}
            className={cx("min-h-10 rounded-xl border px-3 text-sm", picked === r ? "border-ink bg-ink text-paper" : "border-line text-ink hover:border-ink/40")}
          >
            {r === "other" ? "Something else" : r}
          </button>
        ))}
      </div>
      {picked === "other" && (
        <input autoFocus maxLength={500} value={other} onChange={(e) => setOther(e.target.value)} placeholder="A short reason" className={inputCls} />
      )}
      {error && <p className="text-danger">{error}</p>}
      <div className="flex flex-wrap gap-2">
        <Btn tone="danger" busy={busy} disabled={!ok} onClick={() => void send()}>Send to health worker</Btn>
        <Btn tone="ghost" onClick={onBack}>Keep visit</Btn>
      </div>
    </div>
  );
}

function MissedReason({ visit, onSaved }: { visit: Visit; onSaved: () => void }) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      await explainMissedVisit(visit.id, text);
      onSaved();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="flex flex-col gap-2 rounded-2xl border border-line p-4">
      <p className="font-semibold text-ink">Tell your health centre why you missed it</p>
      <input maxLength={500} value={text} onChange={(e) => setText(e.target.value)} placeholder="For example: I was travelling" className={inputCls} />
      {error && <p className="text-danger">{error}</p>}
      <div>
        <Btn tone="primary" busy={busy} disabled={text.trim().length < 5} onClick={() => void save()}>Send reason</Btn>
      </div>
    </div>
  );
}
