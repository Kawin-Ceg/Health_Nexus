import { useT } from "../../i18n";
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  Ban,
  CircleCheck,
  CircleDashed,
  CircleX,
  Clock3,
  Inbox,
  Info,
  Loader2,
  Search,
  TriangleAlert,
  X,
  type LucideIcon,
} from "lucide-react";
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

type Tone = "primary" | "secondary" | "ghost" | "danger" | "success" | "info" | "warn";
const TONES: Record<Tone, string> = {
  primary: "bg-brand text-on-brand hover:shadow-[0_0_48px_rgb(var(--hn-glow))]",
  secondary: "border-[1.5px] border-ink bg-surface text-ink hover:shadow-[0_0_48px_rgb(var(--hn-glow))]",
  ghost: "text-ink-soft hover:bg-paper-raised hover:text-ink",
  danger: "bg-red-600 text-white hover:bg-red-700",
  success: "bg-green-600 text-white hover:bg-green-700",
  info: "bg-blue-600 text-white hover:bg-blue-700",
  warn: "bg-yellow-400 text-yellow-950 hover:bg-yellow-500",
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

export type StatusTone = "success" | "info" | "warn" | "danger" | "neutral" | "progress";

const STATUS_TONE: Record<StatusTone, { icon: LucideIcon; cls: string }> = {
  success: { icon: CircleCheck, cls: "text-green-700" },
  info: { icon: Clock3, cls: "text-blue-700" },
  warn: { icon: TriangleAlert, cls: "text-yellow-600" },
  danger: { icon: CircleX, cls: "text-red-700" },
  neutral: { icon: Ban, cls: "text-ink-soft" },
  progress: { icon: CircleDashed, cls: "text-violet-700" },
};

export function Status({ tone, icon, children, className }: { tone: StatusTone; icon?: LucideIcon; children: ReactNode; className?: string }) {
  const t = STATUS_TONE[tone];
  const Icon = icon ?? t.icon;
  return (
    <span className={cx("inline-flex items-center gap-1.5 whitespace-nowrap text-[13px] font-semibold leading-none", t.cls, className)}>
      <Icon size={15} strokeWidth={2.25} className="shrink-0" aria-hidden="true" />
      <span>{children}</span>
    </span>
  );
}

export function SeverityBadge({ severity, className }: { severity: Severity; className?: string }) {
  const s = SEVERITY[severity];
  const t = useT();
  return (
    <span className={cx("inline-flex items-center gap-1.5 whitespace-nowrap text-[13px] font-semibold leading-none", s.text, className)}>
      <s.icon size={15} strokeWidth={2.25} className="shrink-0" aria-hidden="true" />
      {t(`severity.${severity}`)}
    </span>
  );
}

export const VISIT_STATUS: Record<VisitState, { label: string; tone: StatusTone }> = {
  upcoming: { label: "Upcoming", tone: "info" },
  today: { label: "Later today", tone: "info" },
  due_now: { label: "Happening now", tone: "progress" },
  overdue: { label: "Needs an outcome", tone: "warn" },
  completed: { label: "Done", tone: "success" },
  cancelled: { label: "Cancelled", tone: "neutral" },
  missed: { label: "Missed", tone: "danger" },
};

export function VisitBadge({ state }: { state: VisitState }) {
  const v = VISIT_STATUS[state];
  return <Status tone={v.tone}>{v.label}</Status>;
}

export const ALERT_LEVEL: Record<"high" | "medium" | "low", { label: string; tone: StatusTone; icon: LucideIcon }> = {
  high: { label: "Important", tone: "danger", icon: TriangleAlert },
  medium: { label: "Take note", tone: "warn", icon: AlertCircle },
  low: { label: "For information", tone: "info", icon: Info },
};

export function AlertLevel({ level }: { level: keyof typeof ALERT_LEVEL }) {
  const l = ALERT_LEVEL[level];
  return <Status tone={l.tone} icon={l.icon}>{l.label}</Status>;
}

export function CloseButton({ onClick, label = "Close", className }: { onClick: () => void; label?: string; className?: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      className={cx(
        "grid h-9 w-9 shrink-0 place-items-center rounded-full text-ink-soft transition-colors hover:bg-red-600 hover:text-white focus-visible:outline-2 focus-visible:outline-red-600",
        className,
      )}
    >
      <X size={18} aria-hidden="true" />
    </button>
  );
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

export function SearchInput({ className, onClear, ...rest }: InputHTMLAttributes<HTMLInputElement> & { onClear?: () => void }) {
  const filled = onClear && String(rest.value ?? "").length > 0;
  return (
    <div className={cx("relative", className)}>
      <Search size={18} className="pointer-events-none absolute top-1/2 left-4 -translate-y-1/2 text-ink-muted" aria-hidden="true" />
      <input type="search" {...rest} className={cx(inputCls, "pl-11 [&::-webkit-search-cancel-button]:hidden", filled && "pr-11")} />
      {filled && (
        <button
          type="button"
          onClick={onClear}
          aria-label="Clear search"
          className="hn-close absolute top-1/2 right-2 grid h-7 w-7 -translate-y-1/2 place-items-center rounded-full text-ink-muted"
        >
          <X size={15} aria-hidden="true" />
        </button>
      )}
    </div>
  );
}

export function ClearFilters({ active, onClear, className }: { active: boolean; onClear: () => void; className?: string }) {
  return (
    <button
      type="button"
      onClick={onClear}
      disabled={!active}
      className={cx(
        "inline-flex min-h-11 items-center justify-center gap-1.5 whitespace-nowrap rounded-2xl border px-4 text-sm font-medium transition-colors",
        active ? "border-red-200 text-red-700 hover:border-red-600 hover:bg-red-600 hover:text-white" : "cursor-not-allowed border-line text-ink-muted opacity-60",
        className,
      )}
    >
      <X size={15} aria-hidden="true" /> Clear all
    </button>
  );
}
