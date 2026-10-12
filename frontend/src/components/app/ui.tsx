import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Link } from "react-router-dom";
import { AlertCircle, Inbox, Loader2 } from "lucide-react";
import { SEVERITY, type Severity } from "../../lib/severity";
import type { VisitState } from "../../services/health";

export const cx = (...classes: (string | false | null | undefined)[]) => classes.filter(Boolean).join(" ");

export function PageHeader({ title, lead, actions }: { title: string; lead?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-3xl text-ink md:text-4xl">{title}</h1>
        {lead && <p className="mt-1 max-w-2xl text-sm text-ink-soft">{lead}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function Card({ children, className, title, aside }: { children: ReactNode; className?: string; title?: ReactNode; aside?: ReactNode }) {
  return (
    <section className={cx("rounded-3xl border border-line bg-surface p-5 md:p-6", className)}>
      {(title || aside) && (
        <header className="mb-4 flex flex-wrap items-center justify-between gap-2">
          {title && <h2 className="text-xl text-ink">{title}</h2>}
          {aside}
        </header>
      )}
      {children}
    </section>
  );
}

type Tone = "primary" | "secondary" | "ghost" | "danger";
const TONES: Record<Tone, string> = {
  primary: "bg-brand text-on-brand hover:shadow-[0_0_48px_rgb(var(--hn-glow))]",
  secondary: "border-[1.5px] border-ink bg-surface text-ink hover:shadow-[0_0_48px_rgb(var(--hn-glow))]",
  ghost: "text-ink-soft hover:bg-paper-raised hover:text-ink",
  danger: "bg-danger text-on-danger hover:opacity-90",
};

export function Btn({
  tone = "secondary",
  busy,
  className,
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { tone?: Tone; busy?: boolean }) {
  return (
    <button
      type="button"
      {...rest}
      disabled={rest.disabled || busy}
      aria-busy={busy || undefined}
      className={cx(
        "inline-flex min-h-11 items-center justify-center gap-2 rounded-full px-5 font-display text-[15px] font-[450] transition-[box-shadow,background-color,color] duration-300 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50",
        TONES[tone],
        className,
      )}
    >
      {busy && <Loader2 size={16} className="animate-spin" aria-hidden="true" />}
      {children}
    </button>
  );
}

/** A link that looks like a button: the same pill, type and glow as Btn. */
export function LinkBtn({ to, tone = "secondary", className, children }: { to: string; tone?: "primary" | "secondary" | "ghost"; className?: string; children: ReactNode }) {
  return (
    <Link
      to={to}
      className={cx(
        "inline-flex min-h-11 items-center justify-center gap-2 rounded-full px-5 font-display text-[15px] font-[450] transition-[box-shadow,background-color,color] duration-300",
        TONES[tone],
        className,
      )}
    >
      {children}
    </Link>
  );
}

export function SeverityBadge({ severity, className }: { severity: Severity; className?: string }) {
  const s = SEVERITY[severity];
  const Icon = s.icon;
  return (
    <span className={cx("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold", s.badge, className)}>
      <Icon size={12} aria-hidden="true" />
      {s.label}
    </span>
  );
}

const VISIT_LABEL: Record<VisitState, { label: string; cls: string }> = {
  upcoming: { label: "Upcoming", cls: "bg-brand-soft text-brand" },
  today: { label: "Later today", cls: "bg-brand-soft text-brand" },
  due_now: { label: "Happening now", cls: "bg-warn/15 text-warn" },
  overdue: { label: "Needs an outcome", cls: "bg-danger-soft text-danger" },
  completed: { label: "Done", cls: "bg-success-soft text-success" },
  cancelled: { label: "Cancelled", cls: "bg-paper-raised text-ink-soft" },
  missed: { label: "Nobody there", cls: "bg-danger-soft text-danger" },
};

export function VisitBadge({ state }: { state: VisitState }) {
  const v = VISIT_LABEL[state];
  return <span className={cx("inline-flex rounded-full px-2 py-0.5 text-xs font-semibold", v.cls)}>{v.label}</span>;
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-2 py-10 text-sm text-ink-soft">
      <Loader2 size={18} className="animate-spin" aria-hidden="true" />
      {label}…
    </div>
  );
}

export function ErrorNote({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-wrap items-center gap-3 rounded-xl border border-danger/30 bg-danger-soft p-4 text-sm text-danger">
      <AlertCircle size={18} aria-hidden="true" />
      <span className="flex-1">{message}</span>
      {onRetry && (
        <Btn tone="secondary" onClick={onRetry}>
          Try again
        </Btn>
      )}
    </div>
  );
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-3xl border border-dashed border-line-strong/40 bg-paper px-4 py-12 text-center">
      <span className="grid h-12 w-12 place-items-center rounded-full bg-lime text-olive">
        <Inbox size={22} aria-hidden="true" />
      </span>
      <p className="mt-1 font-display text-xl text-ink">{title}</p>
      {children && <div className="max-w-md text-sm text-ink-soft">{children}</div>}
    </div>
  );
}

export function Stat({ label, value, hint, tone }: { label: string; value: ReactNode; hint?: ReactNode; tone?: "danger" | "warn" }) {
  return (
    <div className="rounded-3xl border border-line bg-surface p-5">
      <p className="text-xs font-semibold uppercase tracking-[0.06em] text-ink-muted">{label}</p>
      <p className={cx("mt-2 font-display text-4xl tabular-nums leading-none", tone === "danger" ? "text-danger" : tone === "warn" ? "text-warn" : "text-ink")}>
        {value}
      </p>
      {hint && <p className="mt-1 text-xs text-ink-soft">{hint}</p>}
    </div>
  );
}

export function Tabs<T extends string>({
  tabs,
  value,
  onChange,
  label,
}: {
  tabs: { id: T; label: ReactNode }[];
  value: T;
  onChange: (id: T) => void;
  label: string;
}) {
  return (
    <div role="tablist" aria-label={label} className="mb-5 inline-flex max-w-full flex-wrap gap-1 rounded-full border border-line bg-paper-raised p-1">
      {tabs.map((t) => (
        <button
          key={t.id}
          type="button"
          role="tab"
          aria-selected={value === t.id}
          onClick={() => onChange(t.id)}
          className={cx(
            "min-h-10 rounded-full px-4 text-sm font-medium transition-colors",
            value === t.id ? "bg-ink text-paper" : "text-ink-soft hover:text-ink",
          )}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

export const inputCls =
  "min-h-11 w-full rounded-2xl border border-line-strong/40 bg-surface px-4 text-sm text-ink placeholder:text-ink-muted focus:border-ink focus:outline-none";

export function Labelled({ label, children, hint }: { label: string; children: ReactNode; hint?: ReactNode }) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="font-medium text-ink">{label}</span>
      {children}
      {hint && <span className="text-xs text-ink-soft">{hint}</span>}
    </label>
  );
}
