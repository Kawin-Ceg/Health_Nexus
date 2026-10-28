import { useEffect, useState, type ReactNode } from "react";
import { Check, X } from "lucide-react";
import type { Visit, VisitType } from "../../services/health";
import { Btn, CloseButton, Labelled, VisitBadge, cx, inputCls } from "./ui";

export const CUTOFF_HOURS = 8;

export const VISIT_TYPE: Record<VisitType, string> = {
  home: "Home visit",
  centre: "Visit at the centre",
  follow_up: "Follow-up",
  vaccination: "Vaccination",
  maternal: "Mother and child care",
  screening: "Health screening",
};

export const changeable = (v: Visit) => v.status === "scheduled" && new Date(v.scheduled_for).getTime() - Date.now() >= CUTOFF_HOURS * 3600_000;

export function StatePill({ visit }: { visit: Visit }) {
  return <VisitBadge state={visit.state} />;
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
          <CloseButton onClick={onClose} />
        </header>
        <div className="overflow-y-auto px-6 py-5">{children}</div>
      </article>
    </div>
  );
}

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

export type StepState = "done" | "current" | "todo" | "failed";

export interface Step {
  title: string;
  state: StepState;
  at?: ReactNode;
  detail?: ReactNode;
}

export function ProcessSteps({ steps, title }: { steps: Step[]; title?: string }) {
  return (
    <section className="rounded-2xl border border-line">
      {title && <h3 className="border-b border-line px-5 py-3.5 text-base font-semibold text-ink">{title}</h3>}
      <ol>
        {steps.map((s, i) => {
          const last = i === steps.length - 1;
          const nextDone = !last && steps[i + 1].state !== "todo";
          return (
            <li key={s.title} className={cx("relative grid grid-cols-[28px_1fr] gap-x-3 px-5 py-4", !last && "border-b border-line")}>
              {!last && (
                <span
                  aria-hidden="true"
                  className={cx("absolute top-[38px] -bottom-[18px] left-[33px] w-0.5", s.state === "done" && nextDone ? "bg-green-600" : "bg-line")}
                />
              )}
              <span className="relative z-10 mt-0.5 grid h-7 place-items-start justify-center">
                <StepMark state={s.state} />
              </span>
              <div className="min-w-0">
                <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-0.5">
                  <p className={cx("text-[15px] font-semibold", s.state === "todo" ? "text-ink-soft" : "text-ink")}>{s.title}</p>
                  {s.at && <p className={cx("text-sm", s.state === "current" ? "italic text-ink-muted" : "tabular-nums text-ink-muted")}>{s.at}</p>}
                </div>
                {s.detail && <div className="mt-1 text-sm text-ink-soft">{s.detail}</div>}
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function StepMark({ state }: { state: StepState }) {
  if (state === "done") {
    return (
      <span className="grid h-5 w-5 place-items-center rounded-full bg-green-600 text-white">
        <Check size={13} strokeWidth={3} aria-hidden="true" />
      </span>
    );
  }
  if (state === "failed") {
    return (
      <span className="grid h-5 w-5 place-items-center rounded-full bg-red-600 text-white">
        <X size={13} strokeWidth={3} aria-hidden="true" />
      </span>
    );
  }
  if (state === "current") {
    return (
      <span className="grid h-5 w-5 place-items-center rounded-full bg-blue-600/15">
        <span className="h-3 w-3 rounded-full bg-blue-600" />
      </span>
    );
  }
  return <span className="h-5 w-5 rounded-full border-2 border-line-strong/50 bg-surface" />;
}

export function Mention({ children }: { children: ReactNode }) {
  return <span className="rounded-md bg-blue-600/10 px-1.5 py-0.5 font-medium text-blue-700">{children}</span>;
}
