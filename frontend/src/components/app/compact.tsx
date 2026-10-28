import { useState, type ReactNode } from "react";
import { CheckCircle2, ChevronRight, XCircle } from "lucide-react";
import { fmtStamp } from "../../lib/format";
import { errorMessage } from "../../services/api";
import type { DismissReason, ResolveBody } from "../../services/phc";
import { useToast } from "./Toaster";
import { Btn, Labelled, Status, cx, inputCls } from "./ui";

export const shortSignal = (signal: string | null) => (signal ? signal.split(" — ")[0] : "Reading outside the usual range");

export function CompactRow({ topic, at, right, onOpen, muted }: { topic: ReactNode; at: string; right?: ReactNode; onOpen: () => void; muted?: boolean }) {
  return (
    <li>
      <button
        type="button"
        onClick={onOpen}
        className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition-colors hover:bg-paper focus-visible:outline-2 focus-visible:outline-ink"
      >
        <span className="min-w-0 flex-1">
          <span className={cx("block truncate font-semibold", muted ? "text-ink-soft" : "text-ink")}>{topic}</span>
          <span className="block text-xs text-ink-muted">{fmtStamp(at)}</span>
        </span>
        <span className="flex shrink-0 flex-wrap items-center justify-end gap-1.5">{right}</span>
        <ChevronRight size={16} className="shrink-0 text-ink-muted" aria-hidden="true" />
      </button>
    </li>
  );
}

export function CompactList({ children, className }: { children: ReactNode; className?: string }) {
  return <ul className={cx("flex flex-col divide-y divide-line", className)}>{children}</ul>;
}

export const RESOLUTION_PILL = {
  open: { label: "Open", tone: "warn" },
  reviewed: { label: "Resolved", tone: "success" },
  dismissed: { label: "Dismissed", tone: "neutral" },
} as const;

export function ResolutionPill({ status }: { status: keyof typeof RESOLUTION_PILL }) {
  const r = RESOLUTION_PILL[status];
  return <Status tone={r.tone}>{r.label}</Status>;
}

const REASONS: { value: DismissReason; label: string }[] = [
  { value: "false_positive", label: "False alarm" },
  { value: "already_treated", label: "Already being treated" },
  { value: "contacted", label: "Contacted, no action needed" },
  { value: "other", label: "Other" },
];

export function FlagActions({ onResolve, resolveLabel = "Resolve", extra }: { onResolve: (body: ResolveBody) => Promise<unknown>; resolveLabel?: string; extra?: ReactNode }) {
  const [dismissing, setDismissing] = useState(false);
  const [reason, setReason] = useState<DismissReason>("contacted");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<"resolve" | "dismiss" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { notify } = useToast();

  const run = async (dismiss: boolean) => {
    setBusy(dismiss ? "dismiss" : "resolve");
    setError(null);
    try {
      await onResolve(dismiss ? { resolution: "dismissed", dismiss_reason: reason, note: note || undefined } : { resolution: "reviewed" });
      notify(dismiss ? { tone: "success", title: "Dismissed", body: "The reason is kept in the audit trail." } : { tone: "success", title: "Resolved" });
    } catch (e) {
      setError(errorMessage(e));
      setBusy(null);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      {dismissing && (
        <div className="grid gap-3 rounded-xl border border-red-200 bg-red-50/60 p-4 sm:grid-cols-2">
          <Labelled label="Why dismiss">
            <select value={reason} onChange={(e) => setReason(e.target.value as DismissReason)} className={inputCls}>
              {REASONS.map((r) => (
                <option key={r.value} value={r.value}>{r.label}</option>
              ))}
            </select>
          </Labelled>
          <Labelled label="Note (optional)">
            <input value={note} maxLength={500} onChange={(e) => setNote(e.target.value)} className={inputCls} />
          </Labelled>
        </div>
      )}
      {error && <p className="text-sm text-danger">{error}</p>}
      <div className="flex flex-wrap gap-3">
        {dismissing ? (
          <>
            <button type="button" disabled={!!busy} onClick={() => void run(true)} className="inline-flex min-h-11 items-center gap-2 rounded-full bg-red-600 px-5 font-semibold text-white hover:bg-red-700 disabled:opacity-50">
              <XCircle size={16} aria-hidden="true" /> {busy ? "Dismissing…" : "Confirm dismiss"}
            </button>
            <Btn tone="ghost" onClick={() => setDismissing(false)}>Back</Btn>
          </>
        ) : (
          <>
            <button type="button" disabled={!!busy} onClick={() => void run(false)} className="inline-flex min-h-11 items-center gap-2 rounded-full bg-green-600 px-5 font-semibold text-white hover:bg-green-700 disabled:opacity-50">
              <CheckCircle2 size={16} aria-hidden="true" /> {busy ? "Resolving…" : resolveLabel}
            </button>
            <button type="button" onClick={() => setDismissing(true)} className="inline-flex min-h-11 items-center gap-2 rounded-full bg-red-600 px-5 font-semibold text-white hover:bg-red-700">
              <XCircle size={16} aria-hidden="true" /> Dismiss
            </button>
            {extra}
          </>
        )}
      </div>
    </div>
  );
}

export function alertTopic(message: string): string {
  const m = message.toLowerCase();
  if (m.includes("visit")) {
    if (m.includes("cancel")) return "Visit cancelled";
    if (m.includes("moved")) return "Visit moved";
    if (m.includes("no outcome") || m.includes("missed")) return "Visit missed";
    return "Visit booked";
  }
  if (m.includes("few days since") || m.includes("last reading")) return "Reading reminder";
  if (m.includes("watch") || m.includes("sync")) return "Smartwatch";
  if (m.includes("flagged")) return "Reading flagged";
  return "Notice";
}
