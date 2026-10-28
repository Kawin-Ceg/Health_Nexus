import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { ChevronRight, type LucideIcon } from "lucide-react";
import { cx } from "./ui";

export const AXIS = {
  ink: "rgb(var(--hn-ink-soft))",
  line: "rgb(var(--hn-line))",
  brand: "rgb(var(--hn-forest))",
  tick: { fill: "rgb(var(--hn-ink-soft))", fontSize: 12 },
  label: { fill: "rgb(var(--hn-ink-soft))", fontSize: 12, fontWeight: 600 },
};

export const FLAG_RED = "#dc2626";
export const CLEAR_GREEN = "#16a34a";

export function Chips<T extends string>({
  options,
  value,
  onChange,
  label,
}: {
  options: { id: T; label: ReactNode }[];
  value: T;
  onChange: (id: T) => void;
  label: string;
}) {
  return (
    <div role="tablist" aria-label={label} className="-mx-1 flex gap-1.5 overflow-x-auto px-1 pb-1">
      {options.map((o) => (
        <button
          key={o.id}
          type="button"
          role="tab"
          aria-selected={o.id === value}
          onClick={() => onChange(o.id)}
          className={cx(
            "min-h-10 shrink-0 whitespace-nowrap rounded-xl border px-3.5 text-sm font-medium transition-colors",
            o.id === value ? "border-ink bg-ink text-paper" : "border-line text-ink-soft hover:border-ink/40 hover:text-ink",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function TipBox({ title, children }: { title: ReactNode; children: ReactNode }) {
  return (
    <div className="min-w-44 rounded-xl border border-line bg-surface px-3 py-2 text-xs shadow-[var(--hn-shadow-md)]">
      <p className="mb-1 font-semibold text-ink">{title}</p>
      <div className="flex flex-col gap-0.5 text-ink-soft">{children}</div>
    </div>
  );
}

export function TipRow({ color, label, value }: { color?: string; label: ReactNode; value: ReactNode }) {
  return (
    <p className="flex items-center justify-between gap-4">
      <span className="inline-flex items-center gap-1.5">
        {color && <span className="h-2.5 w-2.5 rounded-sm" style={{ background: color }} />}
        {label}
      </span>
      <span className="font-semibold tabular-nums text-ink">{value}</span>
    </p>
  );
}

export function Legend({ items }: { items: { color: string; label: ReactNode; faded?: boolean; dashed?: boolean }[] }) {
  return (
    <p className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-ink-soft">
      {items.map((i, n) => (
        <span key={n} className="inline-flex items-center gap-1.5">
          {i.dashed ? (
            <span className="h-0 w-4 border-t-2 border-dashed" style={{ borderColor: i.color }} />
          ) : (
            <span className="h-2.5 w-2.5 rounded-sm" style={{ background: i.color, opacity: i.faded ? 0.4 : 1 }} />
          )}
          {i.label}
        </span>
      ))}
    </p>
  );
}

export type Tone = "neutral" | "danger" | "warn" | "success" | "info" | "violet";

const TINT: Record<Tone, string> = {
  neutral: "bg-paper-raised text-ink",
  danger: "bg-red-50 text-red-700",
  warn: "bg-yellow-50 text-yellow-700",
  success: "bg-green-50 text-green-700",
  info: "bg-blue-50 text-blue-700",
  violet: "bg-violet-50 text-violet-700",
};

export function IconDot({ icon: Icon, tone = "neutral", size = "md" }: { icon: LucideIcon; tone?: Tone; size?: "sm" | "md" }) {
  return (
    <span className={cx("flex shrink-0 items-center justify-center rounded-full", size === "sm" ? "h-9 w-9" : "h-11 w-11", TINT[tone])}>
      <Icon size={size === "sm" ? 16 : 20} aria-hidden="true" />
    </span>
  );
}

export function StatTile({
  icon: Icon,
  label,
  value,
  hint,
  tone = "neutral",
  to,
  valueClass,
}: {
  icon: LucideIcon;
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: Tone;
  to?: string;
  valueClass?: string;
}) {
  const body = (
    <>
      <IconDot icon={Icon} tone={tone} />
      <div className="min-w-0 flex-1">
        <p className="text-sm text-ink-soft">{label}</p>
        <p className={cx("mt-0.5 font-display text-3xl tabular-nums leading-tight", valueClass ?? "text-ink")}>{value}</p>
        {hint && <p className="mt-0.5 text-xs text-ink-soft">{hint}</p>}
      </div>
    </>
  );
  const cls = "flex h-full gap-4 rounded-3xl border border-line bg-surface p-5";
  return to ? (
    <Link to={to} className={cx(cls, "group transition-colors hover:border-ink/30 focus-visible:outline-2 focus-visible:outline-ink")}>
      {body}
      <ChevronRight size={18} className="mt-1 text-ink-muted transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
    </Link>
  ) : (
    <div className={cls}>{body}</div>
  );
}

export function Share({ parts, label }: { parts: { value: number; color: string; label: string }[]; label: string }) {
  const total = parts.reduce((a, p) => a + p.value, 0);
  return (
    <div>
      <div role="img" aria-label={`${label}: ${parts.map((p) => `${p.label} ${p.value}`).join(", ")}`} className="flex h-3 w-full overflow-hidden rounded-full bg-paper-raised">
        {total > 0 &&
          parts.map((p) =>
            p.value > 0 ? <span key={p.label} title={`${p.label}: ${p.value}`} style={{ width: `${(p.value / total) * 100}%`, background: p.color }} /> : null,
          )}
      </div>
      <ul className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
        {parts.map((p) => (
          <li key={p.label} className="flex items-center justify-between gap-2">
            <span className="inline-flex items-center gap-1.5 text-ink-soft">
              <span className="h-2.5 w-2.5 rounded-sm" style={{ background: p.color }} />
              {p.label}
            </span>
            <span className="font-semibold tabular-nums text-ink">{p.value}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
