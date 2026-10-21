import { useState } from "react";
import { cx } from "./ui";

export interface Slice {
  label: string;
  value: number;
  color: string;
}

/**
 * A ring chart whose segments highlight on hover. The hover target is a wide
 * invisible ring over each segment, so small slices are easy to hit.
 */
export function Donut({ slices, caption, size = 76 }: { slices: Slice[]; caption: string; size?: number }) {
  const [active, setActive] = useState<string | null>(null);
  const total = slices.reduce((s, x) => s + x.value, 0);
  const r = 40;
  const c = 2 * Math.PI * r;
  const hit = slices.find((s) => s.label === active);
  let at = 0;
  const arcs = slices.map((s) => {
    const len = total ? (s.value / total) * c : 0;
    const arc = { ...s, len, start: at };
    at += len;
    return arc;
  });

  return (
    <div className="relative shrink-0" style={{ width: size, height: size }} onMouseLeave={() => setActive(null)}>
      <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90" role="img" aria-label={`${total} ${caption}`}>
        <circle cx="50" cy="50" r={r} fill="none" strokeWidth="14" className="stroke-paper-raised" />
        {arcs.map((a) =>
          a.len > 0 ? (
            <circle
              key={a.label}
              cx="50"
              cy="50"
              r={r}
              fill="none"
              stroke={a.color}
              strokeWidth={active === a.label ? 17 : 14}
              strokeDasharray={`${a.len} ${c}`}
              strokeDashoffset={-a.start}
              opacity={active && active !== a.label ? 0.35 : 1}
              className="transition-[opacity,stroke-width] duration-150"
            />
          ) : null,
        )}
        {arcs.map((a) =>
          a.len > 0 ? (
            <circle
              key={`hit-${a.label}`}
              cx="50"
              cy="50"
              r={r}
              fill="none"
              stroke="transparent"
              strokeWidth="26"
              strokeDasharray={`${a.len} ${c}`}
              strokeDashoffset={-a.start}
              className="cursor-pointer"
              onMouseEnter={() => setActive(a.label)}
              onFocus={() => setActive(a.label)}
              onBlur={() => setActive(null)}
              tabIndex={0}
              aria-label={`${a.label}: ${a.value}`}
            />
          ) : null,
        )}
      </svg>
      {hit && (
        <span className="pointer-events-none absolute top-full left-1/2 z-10 mt-1 -translate-x-1/2 whitespace-nowrap rounded-lg bg-ink px-2 py-1 text-xs text-paper shadow">
          {hit.label}: {hit.value}
        </span>
      )}
      <div className="pointer-events-none absolute inset-0 grid place-items-center text-center">
        <p className={cx("text-sm font-semibold tabular-nums text-ink")}>{hit ? hit.value : total}</p>
      </div>
    </div>
  );
}
