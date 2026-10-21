import { useMemo, useState } from "react";
import { CalendarClock, Clock, MapPin, Phone, Stethoscope, UserRound } from "lucide-react";
import { CUTOFF_HOURS, CancelForm, Detail, Modal, StatePill, VISIT_TYPE, changeable } from "../../components/app/visits";
import { useToast } from "../../components/app/Toaster";
import { Btn, Empty, ErrorNote, Loading, PageHeader, SearchInput, cx, inputCls } from "../../components/app/ui";
import { fmtDateTime, fmtVisit } from "../../lib/format";
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
      .filter((v) => !q || `${v.reason ?? ""} ${v.location ?? ""} ${v.worker_name ?? ""}`.toLowerCase().includes(q))
      .sort((a, b) => (tab === "upcoming" ? a.scheduled_for.localeCompare(b.scheduled_for) : b.scheduled_for.localeCompare(a.scheduled_for)));
  }, [visits, tab, search, type, days]);
  const open = visits.find((v) => v.id === openId) ?? null;

  return (
    <>
      <PageHeader title="Visits" lead={`Visits your health centre has booked with you. You can cancel one with a reason up to ${CUTOFF_HOURS} hours before it starts.`} />
      <div className="mb-4 grid gap-3 md:grid-cols-[3fr_2fr]">
        <SearchInput value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search reason, place or health worker" aria-label="Search visits" />
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
      </div>
      <div role="tablist" aria-label="Status" className="mb-5 flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            className={cx("inline-flex min-h-10 items-center gap-2 rounded-full border px-4 text-sm font-medium", tab === t.id ? "border-ink bg-ink text-paper" : "border-line bg-surface text-ink hover:border-ink/40")}
          >
            {t.label} <span className="tabular-nums opacity-70">{counts[t.id]}</span>
          </button>
        ))}
      </div>

      {res.error && <ErrorNote message={res.error} onRetry={res.reload} />}
      {!res.data ? (
        !res.error && <Loading />
      ) : rows.length === 0 ? (
        <Empty title={tab === "upcoming" ? "No visits booked" : "Nothing here"} />
      ) : (
        <ul className="grid gap-5 md:grid-cols-2 2xl:grid-cols-3">
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
                    <span className="block text-base font-semibold leading-snug text-ink">{fmtVisit(v.scheduled_for)}</span>
                    <span className="mt-0.5 block text-ink-muted">{VISIT_TYPE[v.visit_type ?? "home"]} · {v.duration_minutes ?? 30} min</span>
                  </span>
                </span>
                <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2">
                  <dt className="text-ink-muted">With</dt>
                  <dd className="text-ink">{v.worker_name ?? "Your health centre"}</dd>
                  <dt className="text-ink-muted">Where</dt>
                  <dd className="text-ink">{v.location ?? "—"}</dd>
                  {v.reason && (
                    <>
                      <dt className="text-ink-muted">For</dt>
                      <dd className="line-clamp-2 text-ink">{v.reason}</dd>
                    </>
                  )}
                </dl>
                <span className="mt-auto flex items-center justify-between gap-3 border-t border-line pt-4">
                  <span className="text-xs text-ink-muted">
                    {v.status === "missed" && !v.missed_reason ? "Tell us why you missed it" : v.status === "scheduled" && !changeable(v) ? "Too close to change" : ""}
                  </span>
                  <StatePill visit={v} />
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {open && <VisitDetails visit={open} onClose={() => setOpenId(null)} onChanged={res.reload} />}
    </>
  );
}

function VisitDetails({ visit: v, onClose, onChanged }: { visit: Visit; onClose: () => void; onChanged: () => void }) {
  const [cancelling, setCancelling] = useState(false);
  const { notify } = useToast();
  const canChange = changeable(v);

  return (
    <Modal title={fmtVisit(v.scheduled_for)} onClose={onClose}>
      <div className="flex flex-col gap-5">
        <div className="flex flex-wrap items-center gap-2">
          <StatePill visit={v} />
          <span className="text-ink-soft">{VISIT_TYPE[v.visit_type ?? "home"]}</span>
        </div>
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
          <Detail label="Where"><span className="flex items-center gap-1.5"><MapPin size={14} aria-hidden="true" /> {v.location ?? "—"}</span></Detail>
          <Detail label="How long"><span className="flex items-center gap-1.5"><Clock size={14} aria-hidden="true" /> About {v.duration_minutes ?? 30} minutes</span></Detail>
          <Detail label="Reason"><span className="flex items-center gap-1.5"><Stethoscope size={14} aria-hidden="true" /> {v.reason ?? "General check"}</span></Detail>
          <Detail label="Booked for">{fmtDateTime(v.scheduled_for)}</Detail>
        </dl>

        {v.status === "cancelled" && v.cancel_reason && (
          <p className="rounded-xl bg-paper p-3 text-ink">
            Cancelled by {v.cancelled_by === "citizen" ? "you" : "your health centre"}: "{v.cancel_reason}"
          </p>
        )}
        {v.status === "missed" && <MissedReason visit={v} onSaved={onChanged} />}

        {v.status === "scheduled" &&
          (canChange ? (
            cancelling ? (
              <CancelForm
                who="Your health worker"
                onBack={() => setCancelling(false)}
                onCancel={async (reason) => {
                  try {
                    await cancelMyVisit(v.id, reason);
                  } catch (e) {
                    throw new Error(errorMessage(e));
                  }
                  notify({ tone: "success", title: "Visit cancelled", body: "Your health worker has been told why." });
                  onChanged();
                  onClose();
                }}
              />
            ) : (
              <div>
                <Btn tone="ghost" onClick={() => setCancelling(true)}>Cancel this visit</Btn>
              </div>
            )
          ) : (
            <p className="rounded-xl bg-paper p-3 text-ink-soft">
              This visit starts in less than {CUTOFF_HOURS} hours, so it can't be cancelled here. If you can't make it, call your health worker.
            </p>
          ))}
      </div>
    </Modal>
  );
}

/** A missed visit the citizen has not explained counts toward a complaint from their health centre. */
function MissedReason({ visit, onSaved }: { visit: Visit; onSaved: () => void }) {
  const [given, setGiven] = useState(visit.missed_reason ?? null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (given) return <p className="rounded-xl bg-paper p-3 text-ink-soft">Your reason for missing it: "{given}"</p>;
  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      setGiven((await explainMissedVisit(visit.id, text)).missed_reason ?? text);
      onSaved();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="flex flex-col gap-2 rounded-xl border border-line p-4">
      <p className="font-semibold text-ink">Couldn't make it? Tell your health centre why.</p>
      <p className="text-ink-soft">Missed visits without a reason can lead to a complaint from your health centre.</p>
      <textarea rows={2} maxLength={500} value={text} onChange={(e) => setText(e.target.value)} placeholder="For example: I was travelling, or I was in hospital." className={cx(inputCls, "py-2")} />
      {error && <p className="text-danger">{error}</p>}
      <div>
        <Btn tone="primary" busy={busy} disabled={text.trim().length < 5} onClick={() => void save()}>Send reason</Btn>
      </div>
    </div>
  );
}
