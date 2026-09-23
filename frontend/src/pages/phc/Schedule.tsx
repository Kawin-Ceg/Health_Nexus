import { useState } from "react";
import { PersonLine, workerState } from "../../components/app/phc";
import { Btn, Card, Loading, PageHeader, VisitBadge, inputCls } from "../../components/app/ui";
import { fmtVisit, fromLocalInput, toLocalInput } from "../../lib/format";
import { useResource } from "../../lib/useResource";
import { errorMessage } from "../../services/api";
import type { Visit } from "../../services/health";
import { getSchedule, updateVisit } from "../../services/phc";

function VisitRow({ visit, onChanged }: { visit: Visit; onChanged: () => void }) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [moving, setMoving] = useState(false);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [when, setWhen] = useState(() => toLocalInput(new Date(Math.max(Date.now() + 3600_000, new Date(visit.scheduled_for).getTime()))));

  const act = async (action: "complete" | "cancel" | "miss" | "move") => {
    setBusy(action);
    setError(null);
    try {
      await updateVisit(visit.id, action === "move" ? { action, scheduled_for: new Date(fromLocalInput(when)).toISOString() } : { action });
      onChanged();
    } catch (e) {
      setError(errorMessage(e));
      setBusy(null);
    }
  };

  const passed = visit.state === "due_now" || visit.state === "overdue";
  const open = visit.status === "scheduled";

  return (
    <li className="flex flex-col gap-3 py-4">
      <div className="flex flex-wrap items-start gap-4">
        <div className="w-40 shrink-0">
          <p className="font-semibold text-ink">{fmtVisit(visit.scheduled_for)}</p>
          <VisitBadge state={visit.state} />
        </div>
        <div className="min-w-48 flex-1 text-sm">
          {visit.citizen && <PersonLine person={visit.citizen} />}
          {(visit.reason || visit.location) && <p className="mt-1 text-ink-soft">{[visit.reason, visit.location].filter(Boolean).join(" · ")}</p>}
        </div>
        {open && (
          <div className="flex flex-wrap gap-2">
            {visit.state !== "upcoming" && (
              <Btn tone="primary" busy={busy === "complete"} onClick={() => void act("complete")}>Mark done</Btn>
            )}
            {/* Only once the visit time has actually passed. */}
            {passed && <Btn busy={busy === "miss"} onClick={() => void act("miss")}>Nobody there</Btn>}
            <Btn tone="ghost" onClick={() => setMoving((m) => !m)}>Move</Btn>
            {confirmCancel ? (
              <>
                <Btn tone="danger" busy={busy === "cancel"} onClick={() => void act("cancel")}>Confirm cancel</Btn>
                <Btn tone="ghost" onClick={() => setConfirmCancel(false)}>Keep</Btn>
              </>
            ) : (
              <Btn tone="ghost" onClick={() => setConfirmCancel(true)}>Cancel</Btn>
            )}
          </div>
        )}
      </div>
      {moving && (
        <div className="flex flex-wrap items-center gap-2">
          <input type="datetime-local" value={when} min={toLocalInput(new Date())} onChange={(e) => setWhen(e.target.value)} aria-label="New time (India time)" className={`${inputCls} max-w-xs`} />
          <Btn tone="primary" busy={busy === "move"} onClick={() => void act("move")}>Move visit</Btn>
        </div>
      )}
      {error && <p className="text-sm text-danger">{error}</p>}
    </li>
  );
}

const GROUPS = [
  { key: "needs_outcome", title: "Needs an outcome", note: "The visit time passed more than 4 hours ago and nothing was recorded." },
  { key: "happening_now", title: "Happening now", note: "Within 4 hours of the booked time." },
  { key: "today", title: "Later today", note: null },
  { key: "upcoming", title: "Upcoming", note: null },
] as const;

export function Schedule() {
  const sched = useResource((s) => getSchedule(s), "schedule");
  const blocked = workerState(sched);
  if (blocked) return blocked;
  const s = sched.data;

  return (
    <>
      <PageHeader title="Schedule" lead="Your visits. Each one appears in exactly one group." />
      {!s ? <Loading /> : (
        <div className="flex flex-col gap-6">
          {GROUPS.map((g) => (
            <Card key={g.key} title={`${g.title} (${s.counts[g.key]})`} aside={g.note && <span className="text-xs text-ink-soft">{g.note}</span>}>
              {s[g.key].length === 0 ? (
                <p className="text-sm text-ink-soft">Nothing here.</p>
              ) : (
                <ul className="divide-y divide-line">
                  {s[g.key].map((v) => <VisitRow key={v.id} visit={v} onChanged={sched.reload} />)}
                </ul>
              )}
              {s.counts[g.key] > s[g.key].length && <p className="mt-2 text-xs text-ink-soft">Showing {s[g.key].length} of {s.counts[g.key]}.</p>}
            </Card>
          ))}
          <Card title={`Recorded in the last ${s.recent_window_days} days (${s.counts.recent_outcomes})`}>
            {s.recent_outcomes.length === 0 ? <p className="text-sm text-ink-soft">No outcomes recorded.</p> : (
              <ul className="divide-y divide-line">
                {s.recent_outcomes.map((v) => <VisitRow key={v.id} visit={v} onChanged={sched.reload} />)}
              </ul>
            )}
          </Card>
        </div>
      )}
    </>
  );
}
