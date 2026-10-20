import { useEffect, useState, type ReactNode } from "react";
import { X } from "lucide-react";
import type { Visit, VisitType } from "../../services/health";
import { Btn, Labelled, cx, inputCls } from "./ui";

export const CUTOFF_HOURS = 8;

export const VISIT_TYPE: Record<VisitType, string> = {
  home: "Home visit",
  centre: "Visit at the centre",
  follow_up: "Follow-up",
  vaccination: "Vaccination",
  maternal: "Mother and child care",
  screening: "Health screening",
};

/** Booked visits more than 8 hours away can still be cancelled or moved. */
export const changeable = (v: Visit) => v.status === "scheduled" && new Date(v.scheduled_for).getTime() - Date.now() >= CUTOFF_HOURS * 3600_000;

export const STATE_PILL: Record<Visit["state"], { label: string; cls: string }> = {
  upcoming: { label: "Upcoming", cls: "bg-sky-100 text-sky-900" },
  today: { label: "Today", cls: "bg-violet-100 text-violet-900" },
  due_now: { label: "Happening now", cls: "bg-amber-100 text-amber-900" },
  overdue: { label: "Needs outcome", cls: "bg-orange-100 text-orange-900" },
  completed: { label: "Done", cls: "bg-green-100 text-green-900" },
  cancelled: { label: "Cancelled", cls: "bg-paper-raised text-ink-soft" },
  missed: { label: "Missed", cls: "bg-red-100 text-red-900" },
};

export function StatePill({ visit }: { visit: Visit }) {
  const s = STATE_PILL[visit.state];
  return <span className={cx("inline-block rounded-full px-3 py-1 text-xs font-semibold", s.cls)}>{s.label}</span>;
}

export function Modal({ title, onClose, children, wide }: { title: ReactNode; onClose: () => void; children: ReactNode; wide?: boolean }) {
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
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-3 backdrop-blur-sm" onClick={onClose}>
      <article
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
        className={cx("flex max-h-[calc(100dvh-1.5rem)] w-full flex-col overflow-hidden rounded-2xl border border-line bg-surface text-sm shadow-xl", wide ? "max-w-3xl" : "max-w-xl")}
      >
        <header className="flex items-start justify-between gap-4 border-b border-line px-6 py-4">
          <h2 className="text-xl text-ink">{title}</h2>
          <button type="button" onClick={onClose} aria-label="Close" className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-paper text-ink hover:bg-paper-raised">
            <X size={18} aria-hidden="true" />
          </button>
        </header>
        <div className="overflow-y-auto px-6 py-5">{children}</div>
      </article>
    </div>
  );
}

/** Cancelling needs a real reason; the other person sees it. */
export function CancelForm({ onCancel, onBack, who }: { onCancel: (reason: string) => Promise<void>; onBack: () => void; who: string }) {
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const ok = reason.trim().length >= 10;
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-red-200 bg-red-50/60 p-4">
      <Labelled label="Why are you cancelling?" hint={`${reason.trim().length}/500, at least 10 characters. ${who} will see this.`}>
        <textarea rows={3} maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} className={cx(inputCls, "py-2")} />
      </Labelled>
      {error && <p className="text-danger">{error}</p>}
      <div className="flex flex-wrap gap-2">
        <Btn
          tone="danger"
          busy={busy}
          disabled={!ok}
          onClick={async () => {
            setBusy(true);
            setError(null);
            try {
              await onCancel(reason.trim());
            } catch (e) {
              setError(e instanceof Error ? e.message : String(e));
              setBusy(false);
            }
          }}
        >
          Cancel visit
        </Btn>
        <Btn tone="ghost" onClick={onBack}>Keep visit</Btn>
      </div>
    </div>
  );
}

export function Detail({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-sm font-semibold text-ink">{label}</dt>
      <dd className="mt-0.5 text-sm text-ink-soft">{children}</dd>
    </div>
  );
}
