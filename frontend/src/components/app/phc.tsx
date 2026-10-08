import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { Building2, Phone } from "lucide-react";
import { fmtAgo, fmtDateTime, fmtVisit, fromLocalInput, plural, toLocalInput } from "../../lib/format";
import { citizenRecordPath, paths } from "../../lib/routes";
import { getPreferences } from "../../services/account";
import { errorMessage } from "../../services/api";
import type { VisitPerson } from "../../services/health";
import { bookVisit, resolveCitizen, type DismissReason, type ResolveBody, type WorkItem } from "../../services/phc";
import { BasisTag } from "./ModelInsights";
import { Btn, ErrorNote, Labelled, SeverityBadge, VisitBadge, inputCls } from "./ui";

/**
 * Shown instead of any worker page when the API answers 409: the account has no
 * facility. An empty dashboard would read as "a quiet day" and be acted on.
 */
export function NoFacility({ message }: { message: string }) {
  return (
    <div role="alert" className="mx-auto mt-10 max-w-xl rounded-2xl border border-warn/40 bg-surface p-6">
      <Building2 size={28} className="text-warn" aria-hidden="true" />
      <h1 className="mt-3 text-xl font-semibold text-ink">No health centre linked</h1>
      <p className="mt-2 text-sm text-ink">{message}</p>
      <p className="mt-2 text-sm text-ink-soft">
        Until then there is nothing to show here, and that is not the same as nobody needing help. Readings from your
        area are not reaching you.
      </p>
      <Link to={`${paths.settings}?tab=concerns`} className="mt-4 inline-block text-sm font-semibold text-brand underline">
        Contact support
      </Link>
    </div>
  );
}

/** Loading/error/409 handling shared by the worker pages. Returns null when the page should render. */
export function workerState(r: { error: string | null; status: number | null; data: unknown; reload: () => void }) {
  if (r.status === 409 && r.error) return <NoFacility message={r.error} />;
  if (r.error && !r.data) return <ErrorNote message={r.error} onRetry={r.reload} />;
  return null;
}

export function PersonLine({ person, linked = true }: { person: VisitPerson; linked?: boolean }) {
  return (
    <div className="min-w-0">
      {linked ? (
        <Link to={citizenRecordPath(person.id)} className="font-semibold text-ink underline-offset-2 hover:underline">
          {person.name}
        </Link>
      ) : (
        <span className="font-semibold text-ink">{person.name}</span>
      )}
      <p className="flex flex-wrap items-center gap-x-3 text-xs text-ink-soft">
        <span className="font-mono">{person.ref}</span>
        {person.area && <span>{person.area}</span>}
        {person.phone && (
          <a href={`tel:${person.phone.replace(/[^\d+]/g, "")}`} className="inline-flex items-center gap-1 text-brand">
            <Phone size={12} aria-hidden="true" />
            {person.phone}
          </a>
        )}
      </p>
    </div>
  );
}

const REASONS: { value: DismissReason; label: string }[] = [
  { value: "false_positive", label: "False alarm" },
  { value: "already_treated", label: "Already being treated" },
  { value: "contacted", label: "Contacted, no action needed" },
  { value: "other", label: "Other" },
];

/** "Reviewed" in one click; "Dismiss" asks why, because a dismissal without a reason cannot be audited. */
export function ResolveControls({
  onResolve,
  reviewLabel = "Mark seen",
}: {
  onResolve: (body: ResolveBody) => Promise<unknown>;
  reviewLabel?: string;
}) {
  const [mode, setMode] = useState<"idle" | "dismiss">("idle");
  const [reason, setReason] = useState<DismissReason>("contacted");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async (body: ResolveBody) => {
    setBusy(true);
    setError(null);
    try {
      await onResolve(body);
    } catch (e) {
      setError(errorMessage(e));
      setBusy(false);
    }
  };

  if (mode === "dismiss") {
    return (
      <div className="flex flex-wrap items-end gap-2">
        <select aria-label="Why dismiss" value={reason} onChange={(e) => setReason(e.target.value as DismissReason)} className={`${inputCls} w-auto`}>
          {REASONS.map((r) => (
            <option key={r.value} value={r.value}>
              {r.label}
            </option>
          ))}
        </select>
        <input value={note} maxLength={500} onChange={(e) => setNote(e.target.value)} placeholder="Note (optional)" aria-label="Note" className={`${inputCls} w-48`} />
        <Btn tone="primary" busy={busy} onClick={() => void run({ resolution: "dismissed", dismiss_reason: reason, note: note || undefined })}>
          Dismiss
        </Btn>
        <Btn tone="ghost" onClick={() => setMode("idle")}>
          Back
        </Btn>
        {error && <p className="w-full text-sm text-danger">{error}</p>}
      </div>
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Btn tone="primary" busy={busy} onClick={() => void run({ resolution: "reviewed" })}>
        {reviewLabel}
      </Btn>
      <Btn tone="ghost" onClick={() => setMode("dismiss")}>
        Dismiss…
      </Btn>
      {error && <p className="w-full text-sm text-danger">{error}</p>}
    </div>
  );
}

/**
 * One citizen, one piece of work: every open flag for that person in a single
 * card, worst first. The dashboard and the alerts page both render this, so a
 * worker sees the same unit of work wherever they look, and the same person
 * never appears as five separate rows to act on.
 */
export function CitizenWorkCard({ item, onChanged }: { item: WorkItem; onChanged: () => void }) {
  const [booking, setBooking] = useState(false);
  const older = item.open_flags - 1;
  return (
    <li className="rounded-2xl border border-line bg-surface p-4">
      <div className="flex flex-wrap items-start gap-x-4 gap-y-3">
        <div className="min-w-56 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <SeverityBadge severity={item.worst_severity} />
            {item.open_flags > 1 && (
              <span className="rounded-full bg-paper-raised px-2 py-0.5 text-xs font-semibold text-ink-soft">
                {plural(item.open_flags, "open flag")}
              </span>
            )}
          </div>
          <div className="mt-2">
            <PersonLine person={item.citizen} />
          </div>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-ink">
            {item.worst_signal ?? "Reading outside the usual range"} <BasisTag basis={item.flags[0]?.basis ?? null} />
          </p>
          <p className="text-xs text-ink-soft">
            Latest {fmtAgo(item.last_flagged_at)}
            {older > 0 && ` · first flagged ${fmtAgo(item.first_flagged_at)}`}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ResolveControls
            reviewLabel={item.open_flags > 1 ? `Resolve all ${item.open_flags}` : "Mark seen"}
            onResolve={async (body) => {
              await resolveCitizen(item.citizen.id, body);
              onChanged();
            }}
          />
          {!item.next_visit && <Btn onClick={() => setBooking((b) => !b)}>Book visit</Btn>}
          <Link
            to={citizenRecordPath(item.citizen.id)}
            className="inline-flex min-h-11 items-center rounded-xl px-3 text-sm font-semibold text-brand hover:bg-paper-raised"
          >
            Record
          </Link>
        </div>
      </div>
      {item.next_visit && (
        <p className="mt-3 flex flex-wrap items-center gap-2 text-sm text-ink-soft">
          Visit {fmtVisit(item.next_visit.scheduled_for)} <VisitBadge state={item.next_visit.state} />
        </p>
      )}
      {item.flags.length > 1 && (
        <details className="text-sm">
          <summary className="inline-flex min-h-11 w-fit cursor-pointer items-center text-xs font-medium text-ink-soft hover:text-ink">
            {item.open_flags > item.flags_shown
              ? `Show the worst ${item.flags_shown} of ${item.open_flags} flags`
              : `Show all ${item.flags_shown} flags`}
          </summary>
          <ul className="mt-1 flex flex-col gap-1">
            {item.flags.map((f) => (
              <li key={f.processed_id} className="flex flex-wrap items-center gap-2">
                <SeverityBadge severity={f.severity} />
                <span className="text-ink">{f.signal}</span>
                <BasisTag basis={f.basis} />
                <span className="text-xs text-ink-soft">{fmtDateTime(f.measured_at)}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
      {booking && (
        <BookVisitForm
          citizen={item.citizen}
          caseId={item.flags[0]?.processed_id}
          onCancel={() => setBooking(false)}
          onBooked={() => {
            setBooking(false);
            onChanged();
          }}
        />
      )}
    </li>
  );
}

let workingHours: Promise<{ start: string; end: string }> | null = null;

/** The next slot at the start of the worker's working hours, tomorrow. */
function useDefaultSlot() {
  const [slot, setSlot] = useState(() => {
    const d = new Date(Date.now() + 86400_000);
    return `${toLocalInput(d).slice(0, 10)}T10:00`;
  });
  useEffect(() => {
    workingHours ??= getPreferences().then((p) => p.working_hours);
    workingHours
      .then((h) => setSlot((s) => `${s.slice(0, 10)}T${h.start}`))
      .catch(() => undefined);
  }, []);
  return [slot, setSlot] as const;
}

export function BookVisitForm({
  citizen,
  caseId,
  onBooked,
  onCancel,
}: {
  citizen: VisitPerson;
  caseId?: string | null;
  onBooked: () => void;
  onCancel: () => void;
}) {
  const [when, setWhen] = useDefaultSlot();
  const [reason, setReason] = useState("");
  const [location, setLocation] = useState(citizen.area ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await bookVisit({
        citizen_id: citizen.id,
        case_id: caseId ?? undefined,
        scheduled_for: new Date(fromLocalInput(when)).toISOString(),
        reason: reason || undefined,
        location: location || undefined,
      });
      onBooked();
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="mt-3 grid gap-3 rounded-xl border border-line bg-paper-raised p-4 sm:grid-cols-3">
      <p className="text-sm font-semibold text-ink sm:col-span-3">Book a follow-up visit for {citizen.name}</p>
      <Labelled label="When (India time)">
        <input type="datetime-local" required value={when} min={toLocalInput(new Date())} onChange={(e) => setWhen(e.target.value)} className={inputCls} />
      </Labelled>
      <Labelled label="Reason">
        <input value={reason} maxLength={300} onChange={(e) => setReason(e.target.value)} placeholder="e.g. BP check" className={inputCls} />
      </Labelled>
      <Labelled label="Where">
        <input value={location} maxLength={160} onChange={(e) => setLocation(e.target.value)} className={inputCls} />
      </Labelled>
      {error && <p className="text-sm text-danger sm:col-span-3">{error}</p>}
      <div className="flex gap-2 sm:col-span-3">
        <Btn tone="primary" type="submit" busy={busy}>
          Book visit
        </Btn>
        <Btn tone="ghost" onClick={onCancel}>
          Cancel
        </Btn>
      </div>
    </form>
  );
}
