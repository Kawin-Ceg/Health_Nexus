import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowDown, ArrowUp, CalendarClock, Minus, Moon, ShieldAlert, Sun, Sunrise, Sunset } from "lucide-react";
import { Bar, CartesianGrid, ComposedChart, Label, LabelList, ReferenceArea, ResponsiveContainer, Scatter, Tooltip, XAxis, YAxis } from "recharts";
import { Card, Empty, ErrorNote, Loading, PageHeader, VisitBadge, cx } from "../../components/app/ui";
import { TrendChart } from "../../components/app/TrendChart";
import { useAuth } from "../../context/AuthContext";
import { fmtAgo, fmtDateTime, fmtShortDay, fmtVisit, plural } from "../../lib/format";
import { useT } from "../../i18n";
import { paths } from "../../lib/routes";
import { useResource } from "../../lib/useResource";
import { getMetrics, getSummary, type Metric, type Summary } from "../../services/health";

type Point = Summary["trend"][number];
type Latest = Summary["latest"][number];
type Tone = "good" | "watch" | "bad" | "none";

interface Vital {
  metric: Metric;
  latest: Latest | null;
  tone: Tone;
  kept: number;
}

const TONE: Record<Tone, { stroke: string; text: string; label: string; fill: string }> = {
  good: { stroke: "#16a34a", text: "text-green-700", label: "Normal", fill: "bg-green-600" },
  watch: { stroke: "#d97706", text: "text-amber-700", label: "Slightly off", fill: "bg-amber-600" },
  bad: { stroke: "#dc2626", text: "text-red-700", label: "Out of range", fill: "bg-red-600" },
  none: { stroke: "rgb(var(--hn-line))", text: "text-ink-muted", label: "No reading", fill: "bg-line" },
};

const mean = (xs: number[]) => xs.reduce((a, b) => a + b, 0) / xs.length;
const fmt = (m: Metric, v: number) => v.toFixed(m.decimals);

function outside(m: Metric, v: number) {
  if (!m.normal) return 0;
  const [lo, hi] = m.normal;
  const half = (hi - lo) / 2;
  return v < lo ? (lo - v) / half : v > hi ? (v - hi) / half : 0;
}

function vitalsOf(metrics: Metric[], latest: Latest[]): Vital[] {
  return metrics.map((metric) => {
    const l = latest.find((x) => x.key === metric.key) ?? null;
    if (!l) return { metric, latest: null, tone: "none", kept: 0 };
    const d = outside(metric, l.value);
    return { metric, latest: l, tone: d === 0 ? "good" : d < 0.6 ? "watch" : "bad", kept: Math.max(0, 1 - d * 0.8) };
  });
}

function scoreOf(vitals: Vital[], openFlags: number) {
  const scored = vitals.filter((v) => v.latest && v.metric.normal);
  if (!scored.length) return null;
  const base = mean(scored.map((v) => v.kept)) * 100;
  const penalty = Math.min(20, openFlags * 7);
  return { score: Math.max(0, Math.round(base - penalty)), penalty };
}

function rangeText(m: Metric) {
  return m.normal ? `Normal ${m.normal[0]}–${m.normal[1]} ${m.unit}` : "No set range";
}

function VitalTile({ v, active, onHover, onPick }: { v: Vital; active: boolean; onHover: (k: string | null) => void; onPick: (k: string) => void }) {
  const t = TONE[v.tone];
  return (
    <button
      type="button"
      onMouseEnter={() => onHover(v.metric.key)}
      onMouseLeave={() => onHover(null)}
      onFocus={() => onHover(v.metric.key)}
      onBlur={() => onHover(null)}
      onClick={() => onPick(v.metric.key)}
      className={cx(
        "flex w-full items-center gap-3 rounded-2xl border p-3 text-left transition-all",
        active ? "border-ink bg-paper shadow-sm" : "border-line bg-surface hover:border-ink/40",
      )}
    >
      <span className={cx("h-9 w-1.5 shrink-0 rounded-full", t.fill)} aria-hidden="true" />
      <span className="min-w-0 flex-1">
        <span className="block truncate text-xs font-medium text-ink-soft">{v.metric.label}</span>
        <span className="block text-lg font-semibold tabular-nums leading-tight text-ink">
          {v.latest ? fmt(v.metric, v.latest.value) : "—"} <span className="text-xs font-normal text-ink-muted">{v.metric.unit}</span>
        </span>
      </span>
      <span className={cx("shrink-0 text-xs font-semibold", t.text)}>{t.label}</span>
    </button>
  );
}

function HealthRing({ vitals, score, active, onHover, onPick }: {
  vitals: Vital[];
  score: { score: number; penalty: number } | null;
  active: Vital | null;
  onHover: (k: string | null) => void;
  onPick: (k: string) => void;
}) {
  const r = 82;
  const c = 2 * Math.PI * r;
  const seg = c / vitals.length;
  const gap = 5;
  const verdict = !score ? "No readings yet" : score.score >= 85 ? "Looking well" : score.score >= 65 ? "Worth watching" : "Needs attention";

  return (
    <div className="relative mx-auto aspect-square w-full max-w-[280px]">
      <svg viewBox="0 0 200 200" className="h-full w-full -rotate-90" role="img" aria-label={score ? `Health score ${score.score} out of 100` : "Health score"}>
        {vitals.map((v, i) => {
          const on = active?.metric.key === v.metric.key;
          return (
            <circle
              key={v.metric.key}
              cx="100"
              cy="100"
              r={r}
              fill="none"
              stroke={TONE[v.tone].stroke}
              strokeWidth={on ? 22 : 16}
              strokeLinecap="butt"
              strokeDasharray={`${seg - gap} ${c}`}
              strokeDashoffset={-i * seg}
              className={cx("cursor-pointer transition-all duration-200 focus:outline-none", active && !on && "opacity-30")}
              tabIndex={0}
              role="button"
              aria-label={`${v.metric.label}: ${v.latest ? `${fmt(v.metric, v.latest.value)} ${v.metric.unit}` : "no reading"}`}
              onMouseEnter={() => onHover(v.metric.key)}
              onMouseLeave={() => onHover(null)}
              onFocus={() => onHover(v.metric.key)}
              onBlur={() => onHover(null)}
              onClick={() => onPick(v.metric.key)}
              onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onPick(v.metric.key)}
            />
          );
        })}
      </svg>
      <div className="pointer-events-none absolute inset-0 grid place-items-center text-center">
        <div className="max-w-[62%]">
          {active ? (
            <>
              <p className="text-xs font-semibold uppercase tracking-[0.06em] text-ink-soft">{active.metric.label}</p>
              <p className="mt-1 font-display text-3xl leading-tight tabular-nums text-ink">
                {active.latest ? fmt(active.metric, active.latest.value) : "—"}
              </p>
              <p className="text-xs text-ink-soft">{active.metric.unit}</p>
              <p className={cx("mt-1.5 text-sm font-semibold", TONE[active.tone].text)}>{TONE[active.tone].label}</p>
              <p className="text-[11px] text-ink-muted">{rangeText(active.metric)}</p>
            </>
          ) : (
            <>
              <p className="font-display text-6xl leading-none tabular-nums text-ink">{score?.score ?? "—"}</p>
              <p className="mt-1 text-xs text-ink-muted">out of 100</p>
              <p className="mt-1.5 text-sm font-semibold text-ink">{verdict}</p>
              {!!score?.penalty && <p className="text-[11px] text-ink-muted">−{score.penalty} for open flags</p>}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

const SLOTS = [
  { id: "morning", label: "Morning", hours: "5 am – 12 pm", icon: Sunrise, test: (h: number) => h >= 5 && h < 12 },
  { id: "afternoon", label: "Afternoon", hours: "12 – 5 pm", icon: Sun, test: (h: number) => h >= 12 && h < 17 },
  { id: "evening", label: "Evening", hours: "5 – 9 pm", icon: Sunset, test: (h: number) => h >= 17 && h < 21 },
  { id: "night", label: "Night", hours: "9 pm – 5 am", icon: Moon, test: (h: number) => h >= 21 || h < 5 },
] as const;

const hourOf = (iso: string) =>
  Number(new Intl.DateTimeFormat("en-IN", { timeZone: "Asia/Kolkata", hour: "numeric", hourCycle: "h23" }).format(new Date(iso)));

function TimeOfDay({ metric, points }: { metric: Metric; points: Point[] }) {
  const rows = SLOTS.map((s) => {
    const values = points.filter((p) => s.test(hourOf(p.measured_at))).map((p) => p.vitals[metric.key]);
    return {
      slot: s.label,
      hours: s.hours,
      n: values.length,
      avg: values.length ? Number(mean(values).toFixed(metric.decimals)) : null,
      range: values.length ? ([Math.min(...values), Math.max(...values)] as [number, number]) : null,
    };
  });
  const present = rows.filter((r) => r.avg !== null);
  if (present.length === 0) return <p className="text-sm text-ink-soft">No readings in the last 30 days.</p>;

  const all = present.flatMap((r) => r.range!);
  const lo = Math.min(...all, metric.normal?.[0] ?? Infinity);
  const hi = Math.max(...all, metric.normal?.[1] ?? -Infinity);
  const pad = (hi - lo) * 0.2 || 1;
  const domain: [number, number] = [Math.floor(lo - pad), Math.ceil(hi + pad)];
  const top = present.reduce((a, b) => (b.avg! > a.avg! ? b : a));
  const low = present.reduce((a, b) => (b.avg! < a.avg! ? b : a));
  const diff = top.avg! - low.avg!;

  return (
    <div>
      <p className="mb-3 text-sm text-ink">
        {present.length < 2
          ? `Only ${present[0].slot.toLowerCase()} readings so far. Sync at other times to compare.`
          : diff < 10 ** -metric.decimals
            ? "About the same at every time of day."
            : <>Highest in the <strong>{top.slot.toLowerCase()}</strong>, {fmt(metric, diff)} {metric.unit} above the {low.slot.toLowerCase()}.</>}
      </p>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={rows} margin={{ top: 22, right: 8, bottom: 0, left: 12 }}>
            <CartesianGrid stroke="rgb(var(--hn-line))" strokeDasharray="3 4" vertical={false} />
            {metric.normal && <ReferenceArea y1={metric.normal[0]} y2={metric.normal[1]} fill="#16a34a" fillOpacity={0.09} />}
            <XAxis
              dataKey="slot"
              tickLine={false}
              axisLine={{ stroke: "rgb(var(--hn-line))" }}
              interval={0}
              tick={({ x, y, payload }) => {
                const row = rows.find((r) => r.slot === payload.value)!;
                return (
                  <g transform={`translate(${x},${y})`}>
                    <text dy={14} textAnchor="middle" fontSize={12} fontWeight={600} fill="rgb(var(--hn-ink))">{row.slot}</text>
                    <text dy={28} textAnchor="middle" fontSize={10.5} fill="rgb(var(--hn-ink-muted))">{plural(row.n, "reading")}</text>
                  </g>
                );
              }}
              height={40}
            />
            <YAxis domain={domain} tick={{ fill: "rgb(var(--hn-ink-soft))", fontSize: 12 }} axisLine={false} tickLine={false} width={52}>
              <Label value={metric.unit} angle={-90} position="insideLeft" offset={-2} fill="rgb(var(--hn-ink-soft))" fontSize={12} fontWeight={600} style={{ textAnchor: "middle" }} />
            </YAxis>
            <Tooltip
              cursor={{ fill: "rgb(var(--hn-paper))" }}
              content={({ active, payload }) => {
                const row = active && (payload?.[0]?.payload as (typeof rows)[number] | undefined);
                if (!row || row.avg === null) return null;
                return (
                  <div className="rounded-xl border border-line bg-surface px-3 py-2 text-xs shadow-[var(--hn-shadow-md)]">
                    <p className="font-semibold text-ink">{row.slot} <span className="font-normal text-ink-muted">({row.hours})</span></p>
                    <p className="mt-1 text-ink">Average <strong>{fmt(metric, row.avg)} {metric.unit}</strong></p>
                    <p className="text-ink-soft">Lowest {fmt(metric, row.range![0])} · highest {fmt(metric, row.range![1])}</p>
                    <p className="text-ink-muted">{plural(row.n, "reading")}</p>
                  </div>
                );
              }}
            />
            <Bar dataKey="range" barSize={34} radius={8} fill="rgb(var(--hn-matcha))" fillOpacity={0.55} isAnimationActive={false} />
            <Scatter dataKey="avg" fill="rgb(var(--hn-forest))" isAnimationActive={false} shape={(p: { cx?: number; cy?: number; payload?: (typeof rows)[number] }) => {
              if (p.cx === undefined || p.cy === undefined || !p.payload || p.payload.avg === null) return <g />;
              const off = outside(metric, p.payload.avg) > 0;
              return <circle cx={p.cx} cy={p.cy} r={6} fill={off ? "#d97706" : "rgb(var(--hn-forest))"} stroke="rgb(var(--hn-surface))" strokeWidth={2} />;
            }}>
              <LabelList dataKey="avg" position="top" offset={10} fontSize={12} fontWeight={700} fill="rgb(var(--hn-ink))" formatter={(v: unknown) => (v == null ? "" : `${v}`)} />
            </Scatter>
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs text-ink-soft">
        <span className="inline-flex items-center gap-1.5"><span className="h-3 w-3 rounded-full bg-forest" /> Average</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-3 w-2 rounded-sm bg-matcha/60" /> Lowest to highest</span>
        {metric.normal && <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-4 rounded-sm bg-green-600/15" /> {rangeText(metric)}</span>}
      </p>
    </div>
  );
}

interface WeekRow {
  metric: Metric;
  now: number | null;
  before: number | null;
  nNow: number;
  nBefore: number;
}

function weekRows(metrics: Metric[], points: Point[]) {
  const newest = points.reduce((m, p) => Math.max(m, new Date(p.measured_at).getTime()), 0);
  const age = (p: Point) => (newest - new Date(p.measured_at).getTime()) / 86400_000;
  const thisWeek = points.filter((p) => age(p) < 7);
  const lastWeek = points.filter((p) => age(p) >= 7 && age(p) < 14);
  const avg = (ps: Point[], k: string) => {
    const xs = ps.map((p) => p.vitals[k]).filter((v): v is number => v !== undefined);
    return { v: xs.length ? mean(xs) : null, n: xs.length };
  };
  const rows: WeekRow[] = metrics.map((metric) => {
    const a = avg(thisWeek, metric.key);
    const b = avg(lastWeek, metric.key);
    return { metric, now: a.v, before: b.v, nNow: a.n, nBefore: b.n };
  });
  return { rows: rows.filter((r) => r.nNow || r.nBefore), newest };
}

function change(r: WeekRow) {
  if (r.now === null || r.before === null) return null;
  const delta = r.now - r.before;
  const steady = Math.abs(delta) < 10 ** -r.metric.decimals;
  const a = outside(r.metric, r.now);
  const b = outside(r.metric, r.before);
  const better = a < b;
  const worse = a > b;
  return { delta, steady, better, worse };
}

function WeekComparison({ metrics, points }: { metrics: Metric[]; points: Point[] }) {
  const { rows, newest } = useMemo(() => weekRows(metrics, points), [metrics, points]);
  const [focus, setFocus] = useState<string>("all");
  if (!rows.length) return <p className="text-sm text-ink-soft">No readings in the last two weeks.</p>;
  const shown = focus === "all" ? rows : rows.filter((r) => r.metric.key === focus);
  const end = new Date(newest);
  const startNow = new Date(newest - 6 * 86400_000);
  const startBefore = new Date(newest - 13 * 86400_000);
  const endBefore = new Date(newest - 7 * 86400_000);

  return (
    <div className="flex flex-col gap-4">
      <div role="tablist" aria-label="Vital" className="-mx-1 flex gap-1.5 overflow-x-auto px-1 pb-1">
        {[{ key: "all", label: "All" }, ...rows.map((r) => ({ key: r.metric.key, label: r.metric.label }))].map((c) => (
          <button
            key={c.key}
            type="button"
            role="tab"
            aria-selected={focus === c.key}
            onClick={() => setFocus(c.key)}
            className={cx(
              "min-h-9 shrink-0 whitespace-nowrap rounded-lg border px-3 text-xs font-semibold transition-colors",
              focus === c.key ? "border-ink bg-ink text-paper" : "border-line text-ink-soft hover:border-ink/40 hover:text-ink",
            )}
          >
            {c.label}
          </button>
        ))}
      </div>
      <p className="text-xs text-ink-muted">
        This week {fmtShortDay(startNow.toISOString())} – {fmtShortDay(end.toISOString())} against {fmtShortDay(startBefore.toISOString())} – {fmtShortDay(endBefore.toISOString())}
      </p>

      {focus === "all" ? (
        <table className="w-full text-sm">
          <thead className="text-left text-xs text-ink-muted">
            <tr className="border-b border-line">
              <th className="py-2 font-medium">Vital</th>
              <th className="py-2 text-right font-medium">Week before</th>
              <th className="py-2 text-right font-medium">This week</th>
              <th className="py-2 text-right font-medium">Change</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {shown.map((r) => {
              const ch = change(r);
              const Icon = !ch || ch.steady ? Minus : ch.delta > 0 ? ArrowUp : ArrowDown;
              return (
                <tr key={r.metric.key} onClick={() => setFocus(r.metric.key)} className="cursor-pointer hover:bg-paper">
                  <td className="py-2.5 font-medium text-ink">{r.metric.label}</td>
                  <td className="py-2.5 text-right tabular-nums text-ink-soft">{r.before === null ? "—" : fmt(r.metric, r.before)}</td>
                  <td className="py-2.5 text-right font-semibold tabular-nums text-ink">{r.now === null ? "—" : fmt(r.metric, r.now)}</td>
                  <td className={cx("py-2.5 text-right tabular-nums", !ch ? "text-ink-muted" : ch.worse ? "text-red-700" : ch.better ? "text-green-700" : "text-ink-soft")}>
                    <span className="inline-flex items-center gap-1">
                      <Icon size={14} aria-hidden="true" />
                      {!ch ? "—" : ch.steady ? "Steady" : `${ch.delta > 0 ? "+" : ""}${fmt(r.metric, ch.delta)}`}
                      <span className="text-xs font-normal text-ink-muted">{ch && !ch.steady ? r.metric.unit : ""}</span>
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : (
        shown.map((r) => <WeekFocus key={r.metric.key} r={r} />)
      )}
      <p className="text-xs text-ink-muted">
        <span className="font-semibold text-green-700">Green</span>: moving towards normal. <span className="font-semibold text-red-700">Red</span>: moving away from it.
      </p>
    </div>
  );
}

function WeekFocus({ r }: { r: WeekRow }) {
  const m = r.metric;
  const ch = change(r);
  const values = [r.now, r.before, ...(m.normal ?? [])].filter((v): v is number => v !== null);
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const pad = (hi - lo) * 0.25 || 1;
  const pct = (v: number) => ((v - (lo - pad)) / (hi - lo + 2 * pad)) * 100;
  const meaning = !ch
    ? r.now === null
      ? "No readings this week yet."
      : "No readings the week before to compare."
    : !m.normal
      ? ch.steady ? "No real change." : `${ch.delta > 0 ? "Up" : "Down"} on the week before.`
      : ch.better
        ? outside(m, r.now!) === 0 ? "Back inside the normal range." : "Moving back towards normal."
        : ch.worse
          ? outside(m, r.before!) === 0 ? "Moved outside the normal range this week." : "Moving further from normal."
          : outside(m, r.now!) === 0 ? "Inside the normal range both weeks." : "As far from normal as the week before.";

  const bar = (label: string, v: number | null, n: number, strong: boolean) => (
    <div className="grid grid-cols-[92px_1fr_auto] items-center gap-3 text-sm">
      <span className={cx(strong ? "font-semibold text-ink" : "text-ink-soft")}>{label}</span>
      <span className="relative h-7 rounded-lg bg-paper">
        {m.normal && (
          <span className="absolute inset-y-0 rounded-lg bg-green-600/15" style={{ left: `${pct(m.normal[0])}%`, width: `${pct(m.normal[1]) - pct(m.normal[0])}%` }} aria-hidden="true" />
        )}
        {v !== null && (
          <span
            className={cx("absolute inset-y-1 left-1 rounded-md", strong ? "bg-forest" : "bg-matcha/70")}
            style={{ width: `calc(${pct(v)}% - 4px)` }}
            aria-hidden="true"
          />
        )}
      </span>
      <span className="w-28 text-right tabular-nums">
        <span className={cx(strong ? "font-semibold text-ink" : "text-ink-soft")}>{v === null ? "—" : fmt(m, v)}</span>{" "}
        <span className="text-xs text-ink-muted">{m.unit}</span>
        <span className="block text-[11px] text-ink-muted">{plural(n, "reading")}</span>
      </span>
    </div>
  );

  return (
    <div className="flex flex-col gap-3">
      <p className="flex items-baseline gap-2">
        <span className={cx("font-display text-3xl tabular-nums", !ch ? "text-ink" : ch.worse ? "text-red-700" : ch.better ? "text-green-700" : "text-ink")}>
          {!ch ? "—" : ch.steady ? "Steady" : `${ch.delta > 0 ? "+" : ""}${fmt(m, ch.delta)}`}
        </span>
        {ch && !ch.steady && <span className="text-sm text-ink-soft">{m.unit}</span>}
      </p>
      <p className="text-sm font-medium text-ink">{meaning}</p>
      {bar("Week before", r.before, r.nBefore, false)}
      {bar("This week", r.now, r.nNow, true)}
      {m.normal && <p className="text-xs text-ink-muted">Green band: {rangeText(m)}</p>}
    </div>
  );
}

export function CitizenDashboard() {
  const { user } = useAuth();
  const t = useT();
  const { data, error, loading, reload } = useResource((signal) => Promise.all([getSummary(signal), getMetrics()]), "summary");
  const [chosen, setChosen] = useState<string | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);

  const [summary, info] = data ?? [null, null];
  const vitals = useMemo(() => (summary && info ? vitalsOf(info.metrics, summary.latest) : []), [summary, info]);

  if (loading && !data) return <Loading label="Loading your dashboard" />;
  if (error || !summary || !info) return <ErrorNote message={error ?? "Could not load your dashboard."} onRetry={reload} />;

  const score = scoreOf(vitals, summary.open_flags);
  const unreviewed = !summary.facility || summary.facility.workers_assigned === 0;
  const charted = info.metrics.filter((m) => summary.trend.some((p) => p.vitals[m.key] !== undefined));
  const worst = vitals.filter((v) => v.tone === "bad" || v.tone === "watch").sort((a, b) => a.kept - b.kept)[0];
  const metric = charted.find((m) => m.key === chosen) ?? charted.find((m) => m.key === worst?.metric.key) ?? charted[0];
  const series = metric ? summary.trend.filter((p) => p.vitals[metric.key] !== undefined) : [];
  const newest = summary.latest.reduce<string | null>((acc, v) => (!acc || v.measured_at > acc ? v.measured_at : acc), null);
  const active = vitals.find((v) => v.metric.key === hovered) ?? null;
  const half = Math.ceil(vitals.length / 2);

  const pick = (key: string) => {
    if (!charted.some((m) => m.key === key)) return;
    setChosen(key);
    document.getElementById("vital-chart")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <>
      <PageHeader title={t("dash.hello", { name: user?.name.split(" ")[0] ?? "" })} lead={summary.facility ? t("dash.centre", { name: summary.facility.name }) : undefined} />

      {unreviewed && (
        <div role="alert" className="mb-6 flex gap-3 rounded-3xl border border-danger/30 bg-danger-soft p-5 text-sm text-danger">
          <ShieldAlert size={20} aria-hidden="true" className="shrink-0" />
          <p>
            <strong>{t("dash.nobodyTitle")}</strong> {summary.facility ? t("dash.noWorker") : t("dash.noCentre")}{" "}
            <Link to={`${paths.settings}?tab=centre`} className="font-semibold underline">
              {t("dash.chooseCentre")}
            </Link>
            {t("dash.seeDoctor")}
          </p>
        </div>
      )}

      {summary.latest.length === 0 ? (
        <Empty title="No readings yet">
          <Link to={paths.watch} className="font-semibold text-ink underline">Connect your smartwatch</Link> to see your health score.
        </Empty>
      ) : (
        <section aria-labelledby="score-heading" className="mb-6 rounded-3xl border border-line bg-surface p-5 md:p-8">
          <div className="mb-5 flex flex-wrap items-baseline justify-between gap-2">
            <h2 id="score-heading" className="text-xl text-ink">Your health score</h2>
            <p className="text-sm text-ink-muted">Latest readings, {fmtAgo(newest)}</p>
          </div>
          <div className="grid items-center gap-6 lg:grid-cols-[minmax(0,1fr)_300px_minmax(0,1fr)]">
            <ul className="order-2 grid gap-2.5 sm:grid-cols-2 lg:order-1 lg:grid-cols-1">
              {vitals.slice(0, half).map((v) => (
                <li key={v.metric.key}><VitalTile v={v} active={hovered === v.metric.key} onHover={setHovered} onPick={pick} /></li>
              ))}
            </ul>
            <div className="order-1 lg:order-2">
              <HealthRing vitals={vitals} score={score} active={active} onHover={setHovered} onPick={pick} />
            </div>
            <ul className="order-3 grid gap-2.5 sm:grid-cols-2 lg:grid-cols-1">
              {vitals.slice(half).map((v) => (
                <li key={v.metric.key}><VitalTile v={v} active={hovered === v.metric.key} onHover={setHovered} onPick={pick} /></li>
              ))}
            </ul>
          </div>
          <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4 text-xs text-ink-soft">
            <span className="flex flex-wrap gap-x-4 gap-y-1">
              {(["good", "watch", "bad", "none"] as const).map((k) => (
                <span key={k} className="inline-flex items-center gap-1.5"><span className={cx("h-2.5 w-2.5 rounded-full", TONE[k].fill)} /> {TONE[k].label}</span>
              ))}
            </span>
            {summary.next_visit && (
              <Link to={paths.citizenVisits} className="inline-flex flex-wrap items-center gap-2 rounded-xl bg-lime/50 px-3 py-2 text-sm text-ink hover:bg-lime/70">
                <CalendarClock size={16} aria-hidden="true" />
                Visit {fmtVisit(summary.next_visit.scheduled_for)}
                {summary.next_visit.worker_name && ` with ${summary.next_visit.worker_name}`}
                <VisitBadge state={summary.next_visit.state} />
              </Link>
            )}
          </div>
        </section>
      )}

      {metric && (
        <section id="vital-chart" className="mb-6 scroll-mt-6" aria-labelledby="detail-heading">
          <Card
            title={
              <span id="detail-heading">
                {metric.label} <span className="text-base font-normal text-ink-soft">({metric.unit}), last {summary.trend_window_days} days</span>
              </span>
            }
          >
            {charted.length > 1 && (
              <div role="tablist" aria-label="Vital to chart" className="-mx-1 mb-4 flex gap-1.5 overflow-x-auto px-1 pb-1">
                {charted.map((m) => (
                  <button
                    key={m.key}
                    type="button"
                    role="tab"
                    aria-selected={m.key === metric.key}
                    onClick={() => setChosen(m.key)}
                    className={cx(
                      "min-h-10 shrink-0 whitespace-nowrap rounded-xl border px-3.5 text-sm font-medium transition-colors",
                      m.key === metric.key ? "border-ink bg-ink text-paper" : "border-line text-ink-soft hover:border-ink/40 hover:text-ink",
                    )}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
            )}
            {series.length > 0 ? (
              <TrendChart metric={metric} points={series.map((p) => ({ measured_at: p.measured_at, value: p.vitals[metric.key], flagged: p.flagged }))} />
            ) : (
              <Empty title={`No readings in the last ${summary.trend_window_days} days`} />
            )}
          </Card>
          <div className="mt-6 grid items-start gap-6 xl:grid-cols-2">
            <Card title={<>By time of day <span className="text-base font-normal text-ink-soft">· {metric.label} ({metric.unit})</span></>}>
              <TimeOfDay metric={metric} points={series} />
            </Card>
            <Card title="This week against the week before">
              <WeekComparison metrics={charted} points={summary.trend} />
            </Card>
          </div>
        </section>
      )}

      {summary.alerts.length > 0 && (
        <Card title="Latest alerts" aside={<Link to={paths.citizenAlerts} className="text-sm font-semibold text-ink underline underline-offset-4">See all</Link>}>
          <ul className="flex flex-col gap-3">
            {summary.alerts.slice(0, 3).map((a) => (
              <li key={a.id} className="text-sm">
                <p className="text-ink">{a.message}</p>
                <p className="text-xs text-ink-soft">{fmtDateTime(a.created_at)}</p>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </>
  );
}
