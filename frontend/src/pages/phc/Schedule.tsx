import { useMemo, useState, type FormEvent } from "react";
import { CalendarClock, CalendarPlus, Pencil } from "lucide-react";
import { PersonLine, workerState } from "../../components/app/phc";
import { useToast } from "../../components/app/Toaster";
import { Btn, Empty, Labelled, Loading, PageHeader, SearchInput, cx, inputCls } from "../../components/app/ui";
import { CUTOFF_HOURS, CancelForm, Detail, Modal, StatePill, VISIT_TYPE, changeable } from "../../components/app/visits";
import { useDebounced } from "../../lib/useDebounced";
import { fmtDateTime, fmtVisit, fromLocalInput, toLocalInput } from "../../lib/format";
import { useResource } from "../../lib/useResource";
import { errorMessage } from "../../services/api";
import type { Visit, VisitPerson, VisitType } from "../../services/health";
import { bookVisit, getAllVisits, getDirectory, updateVisit } from "../../services/phc";

const TABS = [
  { id: "outcome", label: "Needs outcome", test: (v: Visit) => v.state === "due_now" || v.state === "overdue" },
  { id: "upcoming", label: "Upcoming", test: (v: Visit) => v.state === "today" || v.state === "upcoming" },
  { id: "done", label: "Done", test: (v: Visit) => v.status === "completed" },
  { id: "missed", label: "Missed", test: (v: Visit) => v.status === "missed" },
  { id: "cancelled", label: "Cancelled", test: (v: Visit) => v.status === "cancelled" },
] as const;
type Tab = (typeof TABS)[number]["id"];

const PERIODS = [
  { days: 0, label: "Any time" },
  { days: 1, label: "Within a day" },
  { days: 7, label: "Within 7 days" },
  { days: 30, label: "Within 30 days" },
];

export function Schedule() {
  const res = useResource((s) => getAllVisits(s), "worker-visits");
  const [tab, setTab] = useState<Tab>("upcoming");
  const [search, setSearch] = useState("");
  const [type, setType] = useState("");
  const [days, setDays] = useState(0);
  const [openId, setOpenId] = useState<string | null>(null);
  const [form, setForm] = useState<{ visit?: Visit } | null>(null);

  const visits = res.data?.visits ?? [];
  const counts = Object.fromEntries(TABS.map((t) => [t.id, visits.filter(t.test).length])) as Record<Tab, number>;
  const rows = useMemo(() => {
    const q = search.trim().toLowerCase();
    const test = TABS.find((t) => t.id === tab)!.test;
    return visits
      .filter(test)
      .filter((v) => !type || v.visit_type === type)
      .filter((v) => !days || Math.abs(new Date(v.scheduled_for).getTime() - Date.now()) <= days * 86400_000)
      .filter((v) => !q || `${v.citizen?.name ?? ""} ${v.citizen?.ref ?? ""} ${v.reason ?? ""} ${v.location ?? ""}`.toLowerCase().includes(q))
      .sort((a, b) => (tab === "upcoming" || tab === "outcome" ? a.scheduled_for.localeCompare(b.scheduled_for) : b.scheduled_for.localeCompare(a.scheduled_for)));
  }, [visits, tab, search, type, days]);
  const open = visits.find((v) => v.id === openId) ?? null;

  const blocked = workerState(res);
  if (blocked) return blocked;

  return (
    <>
      <PageHeader
        title="Schedule"
        lead={`Your visits. Visits can be cancelled or moved up to ${CUTOFF_HOURS} hours before they start, and a cancellation needs a reason.`}
        actions={
          <Btn tone="primary" onClick={() => setForm({})}>
            <CalendarPlus size={16} aria-hidden="true" /> Book a visit
          </Btn>
        }
      />
      <div className="mb-4 grid gap-3 md:grid-cols-[3fr_2fr]">
        <SearchInput value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search citizen, reference, reason or place" aria-label="Search visits" />
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

      {!res.data ? (
        <Loading />
      ) : rows.length === 0 ? (
        <Empty title="No visits here" />
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
                    <span className="block text-base font-semibold leading-snug text-ink">{v.citizen?.name ?? "Citizen"}</span>
                    <span className="mt-0.5 block font-mono text-xs text-ink-muted">{v.citizen?.ref}</span>
                  </span>
                  <StatePill visit={v} />
                </span>
                <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2">
                  <dt className="text-ink-muted">When</dt>
                  <dd className="text-ink">{fmtVisit(v.scheduled_for)} · {v.duration_minutes ?? 30} min</dd>
                  <dt className="text-ink-muted">Kind</dt>
                  <dd className="text-ink">{VISIT_TYPE[v.visit_type ?? "home"]}</dd>
                  <dt className="text-ink-muted">Where</dt>
                  <dd className="text-ink">{v.location ?? "—"}</dd>
                  {v.reason && (
                    <>
                      <dt className="text-ink-muted">For</dt>
                      <dd className="line-clamp-2 text-ink">{v.reason}</dd>
                    </>
                  )}
                </dl>
                {v.status === "cancelled" && v.cancelled_by === "citizen" && (
                  <span className="mt-auto rounded-lg bg-amber-50 p-2 text-xs text-amber-900">Cancelled by the citizen: "{v.cancel_reason}"</span>
                )}
                {v.status === "missed" && (
                  <span className="mt-auto text-xs text-ink-muted">{v.missed_reason ? `Citizen's reason: "${v.missed_reason}"` : "No reason given yet"}</span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}

      {open && !form && <VisitDetails visit={open} onClose={() => setOpenId(null)} onEdit={() => setForm({ visit: open })} onChanged={res.reload} />}
      {form && (
        <VisitForm
          visit={form.visit}
          onClose={() => setForm(null)}
          onSaved={() => {
            setForm(null);
            res.reload();
          }}
        />
      )}
    </>
  );
}

function VisitDetails({ visit: v, onClose, onEdit, onChanged }: { visit: Visit; onClose: () => void; onEdit: () => void; onChanged: () => void }) {
  const [busy, setBusy] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { notify } = useToast();
  const name = v.citizen?.name ?? "the citizen";

  const act = async (action: "complete" | "miss", done: string) => {
    setBusy(action);
    setError(null);
    try {
      await updateVisit(v.id, { action });
      notify({ tone: "success", title: done, body: name });
      onChanged();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(null);
    }
  };
  const passed = v.state === "due_now" || v.state === "overdue";
  const booked = v.status === "scheduled";

  return (
    <Modal title={name} onClose={onClose} wide>
      <div className="flex flex-col gap-5">
        <div className="flex flex-wrap items-center gap-3">
          <StatePill visit={v} />
          {v.citizen && <PersonLine person={v.citizen} />}
        </div>
        <dl className="grid gap-4 sm:grid-cols-3">
          <Detail label="When">{fmtDateTime(v.scheduled_for)}</Detail>
          <Detail label="How long">{v.duration_minutes ?? 30} minutes</Detail>
          <Detail label="Kind">{VISIT_TYPE[v.visit_type ?? "home"]}</Detail>
          <Detail label="Where">{v.location ?? "—"}</Detail>
          <Detail label="Reason">{v.reason ?? "—"}</Detail>
          <Detail label="Your notes">{v.notes ?? "—"}</Detail>
        </dl>
        {v.status === "cancelled" && v.cancel_reason && (
          <p className="rounded-xl bg-paper p-3 text-ink">Cancelled by {v.cancelled_by === "citizen" ? "the citizen" : "you"}: "{v.cancel_reason}"</p>
        )}
        {v.status === "missed" && (
          <p className="rounded-xl bg-paper p-3 text-ink">{v.missed_reason ? `The citizen's reason: "${v.missed_reason}"` : "The citizen has not given a reason yet."}</p>
        )}
        {error && <p className="text-danger">{error}</p>}
        {booked &&
          (cancelling ? (
            <CancelForm
              who={name}
              onBack={() => setCancelling(false)}
              onCancel={async (reason) => {
                try {
                  await updateVisit(v.id, { action: "cancel", cancel_reason: reason });
                } catch (e) {
                  throw new Error(errorMessage(e));
                }
                notify({ tone: "success", title: "Visit cancelled", body: `${name} has been told why.` });
                onChanged();
                onClose();
              }}
            />
          ) : (
            <div className="flex flex-wrap gap-2">
              {v.state !== "upcoming" && (
                <Btn tone="primary" busy={busy === "complete"} onClick={() => void act("complete", "Visit marked done")}>Mark done</Btn>
              )}
              {passed && <Btn busy={busy === "miss"} onClick={() => void act("miss", "Marked as nobody there")}>Nobody there</Btn>}
              <Btn tone="ghost" onClick={onEdit}>
                <Pencil size={15} aria-hidden="true" /> Edit
              </Btn>
              {changeable(v) && <Btn tone="ghost" onClick={() => setCancelling(true)}>Cancel visit</Btn>}
            </div>
          ))}
        {booked && !changeable(v) && !passed && (
          <p className="text-ink-soft">Less than {CUTOFF_HOURS} hours to go: the time can't be changed and the visit can't be cancelled. You can still edit the other details.</p>
        )}
      </div>
    </Modal>
  );
}

function defaultSlot(): string {
  const d = new Date(Date.now() + 86400_000);
  return `${toLocalInput(d).slice(0, 10)}T10:00`;
}

/** Book a new visit or edit one. The time can only change while the visit is more than 8 hours away. */
function VisitForm({ visit, onClose, onSaved }: { visit?: Visit; onClose: () => void; onSaved: () => void }) {
  const editing = !!visit;
  const [citizen, setCitizen] = useState<VisitPerson | null>(visit?.citizen ?? null);
  const [query, setQuery] = useState("");
  const q = useDebounced(query);
  const found = useResource((s) => (editing || citizen ? Promise.resolve(null) : getDirectory({ q, limit: 8, offset: 0 }, s)), `pick-${q}-${!!citizen}`);
  const initial = visit ? toLocalInput(new Date(visit.scheduled_for)) : defaultSlot();
  const [date, setDate] = useState(initial.slice(0, 10));
  const [time, setTime] = useState(initial.slice(11, 16));
  const [duration, setDuration] = useState(visit?.duration_minutes ?? 30);
  const [type, setType] = useState<VisitType>(visit?.visit_type ?? "home");
  const [location, setLocation] = useState(visit?.location ?? "");
  const [reason, setReason] = useState(visit?.reason ?? "");
  const [notes, setNotes] = useState(visit?.notes ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { notify } = useToast();
  const timeLocked = editing && !changeable(visit);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!citizen) return;
    setBusy(true);
    setError(null);
    const at = new Date(fromLocalInput(`${date}T${time}`)).toISOString();
    const fields = { reason, location, visit_type: type, duration_minutes: duration, notes };
    try {
      if (visit) {
        const moved = at !== new Date(visit.scheduled_for).toISOString();
        await updateVisit(visit.id, { action: "edit", ...fields, ...(moved ? { scheduled_for: at } : {}) });
        notify({ tone: "success", title: "Visit updated", body: moved ? `${citizen.name} has been told the new time.` : citizen.name });
      } else {
        await bookVisit({ citizen_id: citizen.id, scheduled_for: at, ...fields, location: location || undefined, reason: reason || undefined, notes: notes || undefined });
        notify({ tone: "success", title: "Visit booked", body: `${citizen.name}, ${fmtVisit(at)}. They have been notified.` });
      }
      onSaved();
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  };

  return (
    <Modal title={editing ? "Edit visit" : "Book a visit"} onClose={onClose} wide>
      <form onSubmit={submit} className="flex flex-col gap-5">
        <Labelled label="Citizen">
          {citizen ? (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-line px-3 py-2">
              <PersonLine person={citizen} linked={false} />
              {!editing && (
                <button type="button" onClick={() => setCitizen(null)} className="text-sm text-ink-soft underline underline-offset-4">Change</button>
              )}
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              <SearchInput autoFocus value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search name or HN reference" aria-label="Find a citizen" />
              <ul className="flex max-h-48 flex-col divide-y divide-line overflow-y-auto rounded-xl border border-line">
                {!found.data ? (
                  <li className="p-3"><Loading /></li>
                ) : found.data.items.length === 0 ? (
                  <li className="p-3 text-ink-soft">No citizen matches.</li>
                ) : (
                  found.data.items.map((it) => (
                    <li key={it.citizen.id}>
                      <button
                        type="button"
                        onClick={() => { setCitizen(it.citizen); setLocation((l) => l || it.citizen.area || ""); }}
                        className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left hover:bg-paper"
                      >
                        <span className="font-semibold text-ink">{it.citizen.name}</span>
                        <span className="font-mono text-xs text-ink-muted">{it.citizen.ref}{it.citizen.area ? ` · ${it.citizen.area}` : ""}</span>
                      </button>
                    </li>
                  ))
                )}
              </ul>
            </div>
          )}
        </Labelled>

        <div className="grid gap-4 sm:grid-cols-3">
          <Labelled label="Date">
            <input type="date" required disabled={timeLocked} value={date} min={toLocalInput(new Date()).slice(0, 10)} onChange={(e) => setDate(e.target.value)} className={inputCls} />
          </Labelled>
          <Labelled label="Time (India)">
            <input type="time" required disabled={timeLocked} value={time} step={900} onChange={(e) => setTime(e.target.value)} className={inputCls} />
          </Labelled>
          <Labelled label="Length">
            <select value={duration} onChange={(e) => setDuration(Number(e.target.value))} className={inputCls}>
              {[15, 30, 45, 60, 90, 120].map((m) => (
                <option key={m} value={m}>{m} minutes</option>
              ))}
            </select>
          </Labelled>
        </div>
        {timeLocked && <p className="-mt-2 text-xs text-warn">Less than {CUTOFF_HOURS} hours to go, so the date and time are locked.</p>}

        <div className="grid gap-4 sm:grid-cols-2">
          <Labelled label="Kind of visit">
            <select value={type} onChange={(e) => setType(e.target.value as VisitType)} className={inputCls}>
              {Object.entries(VISIT_TYPE).map(([k, label]) => (
                <option key={k} value={k}>{label}</option>
              ))}
            </select>
          </Labelled>
          <Labelled label="Where">
            <input value={location} maxLength={160} onChange={(e) => setLocation(e.target.value)} placeholder={type === "centre" ? "Mylapore PHC" : "The citizen's home"} className={inputCls} />
          </Labelled>
        </div>
        <Labelled label="Reason" hint="The citizen sees this.">
          <input value={reason} maxLength={300} onChange={(e) => setReason(e.target.value)} placeholder="e.g. Blood pressure follow-up" className={inputCls} />
        </Labelled>
        <Labelled label="Notes for yourself" hint="Only you see these.">
          <textarea rows={3} maxLength={1000} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="e.g. Bring the BP cuff; ask about medicines" className={cx(inputCls, "py-2")} />
        </Labelled>
        {error && <p className="text-danger">{error}</p>}
        <div className="flex gap-2">
          <Btn tone="primary" type="submit" busy={busy} disabled={!citizen}>{editing ? "Save changes" : "Book visit"}</Btn>
          <Btn tone="ghost" onClick={onClose}>Close</Btn>
        </div>
      </form>
    </Modal>
  );
}
