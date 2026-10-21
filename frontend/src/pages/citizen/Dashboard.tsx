import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowDown, ArrowUp, CalendarClock, Minus, ShieldAlert, Watch } from "lucide-react";
import { Card, Empty, ErrorNote, LinkBtn, Loading, PageHeader, VisitBadge, cx } from "../../components/app/ui";
import { TrendChart } from "../../components/app/TrendChart";
import { useAuth } from "../../context/AuthContext";
import { fmtAgo, fmtDateTime, fmtVisit, plural } from "../../lib/format";
import { useLabel, useT } from "../../i18n";
import { paths } from "../../lib/routes";
import { useResource } from "../../lib/useResource";
import { getMetrics, getSummary, type Metric, type Summary } from "../../services/health";

type Point = Summary["trend"][number];
type Latest = Summary["latest"][number];

interface Factor {
  key: string;
  name: string;
  points: number; // 0..max: what this factor contributes to the score
  max: number;
  tone: "good" | "watch" | "bad";
  value: string;
  reason: string;
  vital?: string;
}

const TONE = {
  good: { stroke: "stroke-success", text: "text-success", dot: "bg-success" },
  watch: { stroke: "stroke-warn", text: "text-warn", dot: "bg-warn" },
  bad: { stroke: "stroke-danger", text: "text-danger", dot: "bg-danger" },
} as const;

const mean = (xs: number[]) => xs.reduce((a, b) => a + b, 0) / xs.length;

/** How far outside its normal band a value is, in half-band widths (0 inside). */
function outside(m: Metric, v: number) {
  if (!m.normal) return 0;
  const [lo, hi] = m.normal;
  const half = (hi - lo) / 2;
  return v < lo ? (lo - v) / half : v > hi ? (v - hi) / half : 0;
}

function factorsOf(latest: Latest[], metrics: Map<string, Metric>, label: (k: string, f?: string) => string, openFlags: number, flagged: string[]): Factor[] {
  const vitals = latest.filter((v) => metrics.get(v.key)?.normal);
  const share = vitals.length ? 80 / vitals.length : 0;
  const out: Factor[] = vitals.map((v) => {
    const m = metrics.get(v.key)!;
    const d = outside(m, v.value);
    const kept = Math.max(0, 1 - d * 0.8);
    const name = label(v.key, m.label);
    const value = `${v.value.toFixed(m.decimals)} ${m.unit}`;
    return {
      key: v.key,
      vital: v.key,
      name,
      max: share,
      points: share * kept,
      tone: d === 0 ? "good" : d < 0.6 ? "watch" : "bad",
      value,
      reason:
        d === 0
          ? `Inside the normal ${m.normal![0]}–${m.normal![1]} ${m.unit}.`
          : `${v.value < m.normal![0] ? "Below" : "Above"} the normal ${m.normal![0]}–${m.normal![1]} ${m.unit}, so it costs ${Math.round(share * (1 - kept))} of its ${Math.round(share)} points.`,
    };
  });
  const flagCost = Math.min(20, openFlags * 7);
  out.push({
    key: "flags",
    name: "Open flags",
    max: 20,
    points: 20 - flagCost,
    tone: openFlags === 0 ? "good" : openFlags < 3 ? "watch" : "bad",
    value: openFlags === 0 ? "None" : plural(openFlags, "flag"),
    reason:
      openFlags === 0
        ? "No flagged reading is waiting for review."
        : `${flagged.length ? `Flagged: ${flagged.join("; ")}. ` : ""}Each flagged reading not yet reviewed by your health centre costs 7 points.`,
  });
  return out;
}

/** The health score as a ring: one arc per factor, filled by what it keeps of its share. */
function HealthRing({ factors, active, onHover, onPick }: {
  factors: Factor[];
  active: Factor | null;
  onHover: (f: Factor | null) => void;
  onPick: (f: Factor) => void;
}) {
  const score = Math.round(factors.reduce((s, f) => s + f.points, 0));
  const r = 80;
  const c = 2 * Math.PI * r;
  const gap = factors.length > 1 ? 4 : 0;
  let at = 0;
  const arcs = factors.map((f) => {
    const len = (f.max / 100) * c;
    const arc = { f, start: at, len: Math.max(0, len - gap), fill: Math.max(0, (f.points / f.max) * len - gap) };
    at += len;
    return arc;
  });
  const verdict = score >= 85 ? "Looking well" : score >= 65 ? "Worth watching" : "Needs attention";

  return (
    <div className="relative mx-auto aspect-square w-full max-w-[260px]">
      <svg viewBox="0 0 200 200" className="h-full w-full -rotate-90" role="img" aria-label={`Health score ${score} out of 100`}>
        {arcs.map(({ f, start, len, fill }) => (
          <g key={f.key}>
            <circle cx="100" cy="100" r={r} fill="none" strokeWidth="18" className="stroke-paper-raised" strokeDasharray={`${len} ${c}`} strokeDashoffset={-start} />
            <circle
              cx="100"
              cy="100"
              r={r}
              fill="none"
              strokeWidth={18}
              className={cx(TONE[f.tone].stroke, "cursor-pointer transition-opacity duration-200 focus:outline-none", active && active.key !== f.key && "opacity-35")}
              strokeDasharray={`${fill} ${c}`}
              strokeDashoffset={-start}
              tabIndex={0}
              role="button"
              aria-label={`${f.name}: ${f.value}. ${f.reason}`}
              onMouseEnter={() => onHover(f)}
              onMouseLeave={() => onHover(null)}
              onFocus={() => onHover(f)}
              onBlur={() => onHover(null)}
              onClick={() => onPick(f)}
              onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onPick(f)}
            />
          </g>
        ))}
      </svg>
      <div className="pointer-events-none absolute inset-0 grid place-items-center text-center">
        <div className="max-w-[60%]">
          {active ? (
            <>
              <p className={cx("text-xs font-semibold uppercase tracking-[0.06em]", TONE[active.tone].text)}>{active.name}</p>
              <p className="font-display text-2xl leading-tight text-ink">{active.value}</p>
              <p className="mt-1 text-[11px] leading-snug text-ink-soft">
                {Math.round(active.points)} / {Math.round(active.max)} points
              </p>
            </>
          ) : (
            <>
              <p className="font-display text-5xl leading-none tabular-nums text-ink">{score}</p>
              <p className="mt-1 text-xs text-ink-muted">of 100</p>
              <p className="mt-1 text-sm font-semibold text-ink">{verdict}</p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

const SLOTS = [
  { id: "morning", label: "Morning", test: (h: number) => h >= 5 && h < 12 },
  { id: "afternoon", label: "Afternoon", test: (h: number) => h >= 12 && h < 17 },
  { id: "evening", label: "Evening", test: (h: number) => h >= 17 && h < 21 },
  { id: "night", label: "Night", test: (h: number) => h >= 21 || h < 5 },
] as const;

const hourOf = (iso: string) =>
  Number(new Intl.DateTimeFormat("en-IN", { timeZone: "Asia/Kolkata", hour: "numeric", hourCycle: "h23" }).format(new Date(iso)));

function TimeOfDay({ metric, points }: { metric: Metric; points: Point[] }) {
  const rows = SLOTS.map((s) => {
    const values = points.filter((p) => s.test(hourOf(p.measured_at))).map((p) => p.vitals[metric.key]);
    return { ...s, n: values.length, avg: values.length ? mean(values) : null };
  });
  const present = rows.filter((r) => r.avg !== null) as (typeof rows[number] & { avg: number })[];
  if (present.length === 0) return <p className="text-sm text-ink-soft">No readings in the last 30 days.</p>;
  const values = present.map((r) => r.avg);
  const lo = Math.min(...values, metric.normal?.[0] ?? Infinity);
  const hi = Math.max(...values, metric.normal?.[1] ?? -Infinity);
  const pad = (hi - lo) * 0.15 || 1;
  const pct = (v: number) => ((v - (lo - pad)) / (hi - lo + 2 * pad)) * 100;
  const top = present.reduce((a, b) => (b.avg > a.avg ? b : a));
  const low = present.reduce((a, b) => (b.avg < a.avg ? b : a));
  const diff = top.avg - low.avg;
  return (
    <div>
      <p className="mb-4 text-sm text-ink-soft">
        {present.length < 2
          ? `So far only ${present[0].label.toLowerCase()} readings. Sync at other times to compare.`
          : diff < 10 ** -metric.decimals
            ? "About the same at every time of day."
            : `Highest in the ${top.label.toLowerCase()}, ${diff.toFixed(metric.decimals)} ${metric.unit} above the ${low.label.toLowerCase()}.`}
      </p>
      <ul className="flex flex-col gap-3">
        {rows.map((r) => (
          <li key={r.id} className="grid grid-cols-[80px_1fr_64px] items-center gap-3 text-sm">
            <span className="font-medium text-ink">{r.label}</span>
            <span className="relative h-6 rounded-full bg-paper">
              {metric.normal && (
                <span
                  className="absolute inset-y-0 rounded-full bg-success-soft"
                  style={{ left: `${pct(metric.normal[0])}%`, width: `${pct(metric.normal[1]) - pct(metric.normal[0])}%` }}
                  aria-hidden="true"
                />
              )}
              {r.avg !== null && (
                <span
                  className={cx(
                    "absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-surface",
                    outside(metric, r.avg) > 0 ? "bg-warn" : "bg-ink",
                  )}
                  style={{ left: `${pct(r.avg)}%` }}
                  aria-hidden="true"
                />
              )}
            </span>
            <span className="text-right tabular-nums text-ink">{r.avg === null ? <span className="text-ink-muted">—</span> : r.avg.toFixed(metric.decimals)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** This week against the week before: the change, whether it moves towards or away from normal, and flags. */
function WeekComparison({ metric, points }: { metric: Metric; points: Point[] }) {
  const now = Date.now();
  const age = (p: Point) => (now - new Date(p.measured_at).getTime()) / 86400_000;
  const thisWeek = points.filter((p) => age(p) < 7);
  const lastWeek = points.filter((p) => age(p) >= 7 && age(p) < 14);
  if (!thisWeek.length || !lastWeek.length) {
    return <p className="text-sm text-ink-soft">Needs readings in both of the last two weeks.</p>;
  }
  const a = mean(thisWeek.map((p) => p.vitals[metric.key]));
  const b = mean(lastWeek.map((p) => p.vitals[metric.key]));
  const delta = a - b;
  const steady = Math.abs(delta) < 10 ** -metric.decimals;
  const before = outside(metric, b);
  const after = outside(metric, a);
  const flagsNow = thisWeek.filter((p) => p.flagged).length;
  const flagsBefore = lastWeek.filter((p) => p.flagged).length;
  const Icon = steady ? Minus : delta > 0 ? ArrowUp : ArrowDown;

  let meaning: string;
  if (!metric.normal) meaning = steady ? "No real change." : `${delta > 0 ? "Up" : "Down"} on the week before.`;
  else if (after === 0 && before === 0) meaning = "Inside the normal range both weeks.";
  else if (after < before) meaning = after === 0 ? "Back inside the normal range." : "Moving back towards the normal range.";
  else if (after > before) meaning = before === 0 ? "Moved outside the normal range this week." : "Moving further from the normal range.";
  else meaning = "As far from the normal range as the week before.";

  return (
    <div className="flex flex-col gap-3 text-sm">
      <p className="flex items-baseline gap-2">
        <Icon size={18} className="self-center text-ink" aria-hidden="true" />
        <span className="font-display text-3xl tabular-nums text-ink">{steady ? "Steady" : `${delta > 0 ? "+" : ""}${delta.toFixed(metric.decimals)}`}</span>
        {!steady && <span className="text-ink-soft">{metric.unit}</span>}
      </p>
      <p className={cx("font-medium", after > before ? "text-warn" : after < before ? "text-success" : "text-ink")}>{meaning}</p>
      <dl className="grid grid-cols-2 gap-2">
        <div className="rounded-2xl bg-paper p-3">
          <dt className="text-xs text-ink-muted">This week</dt>
          <dd className="font-display text-xl tabular-nums text-ink">{a.toFixed(metric.decimals)}</dd>
          <dd className="text-xs text-ink-muted">{plural(thisWeek.length, "reading")} · {plural(flagsNow, "flag")}</dd>
        </div>
        <div className="rounded-2xl bg-paper p-3">
          <dt className="text-xs text-ink-muted">Week before</dt>
          <dd className="font-display text-xl tabular-nums text-ink">{b.toFixed(metric.decimals)}</dd>
          <dd className="text-xs text-ink-muted">{plural(lastWeek.length, "reading")} · {plural(flagsBefore, "flag")}</dd>
        </div>
      </dl>
    </div>
  );
}

export function CitizenDashboard() {
  const { user } = useAuth();
  const t = useT();
  const label = useLabel();
  const { data, error, loading, reload } = useResource((signal) => Promise.all([getSummary(signal), getMetrics()]), "summary");
  const [chosen, setChosen] = useState<string | null>(null);
  const [hovered, setHovered] = useState<Factor | null>(null);

  const [summary, info] = data ?? [null, null];
  const metrics = useMemo(() => new Map((info?.metrics ?? []).map((m) => [m.key, m])), [info]);

  if (loading && !data) return <Loading label="Loading your dashboard" />;
  if (error || !summary || !info) return <ErrorNote message={error ?? "Could not load your dashboard."} onRetry={reload} />;

  const vitalLabel = (k: string, f?: string) => label("vital", k, f);
  const flaggedReasons = summary.alerts
    .map((a) => /was flagged: ([^.]+)\./.exec(a.message)?.[1])
    .filter((s): s is string => !!s)
    .filter((s, i, all) => all.indexOf(s) === i)
    .slice(0, 2);
  const factors = factorsOf(summary.latest, metrics, vitalLabel, summary.open_flags, flaggedReasons);
  const unreviewed = !summary.facility || summary.facility.workers_assigned === 0;
  const charted = info.metrics.filter((m) => summary.trend.some((p) => p.vitals[m.key] !== undefined));
  const worst = factors.filter((f) => f.vital && f.tone !== "good").sort((x, y) => x.points / x.max - y.points / y.max)[0];
  const metric = metrics.get(chosen ?? "") ?? metrics.get(worst?.vital ?? "") ?? charted[0];
  const series = metric ? summary.trend.filter((p) => p.vitals[metric.key] !== undefined) : [];
  const newest = summary.latest.reduce<string | null>((acc, v) => (!acc || v.measured_at > acc ? v.measured_at : acc), null);
  const shown = hovered ?? null;

  const pick = (f: Factor) => {
    if (!f.vital) return;
    setChosen(f.vital);
    document.getElementById("vital-chart")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <>
      <PageHeader
        title={t("dash.hello", { name: user?.name.split(" ")[0] ?? "" })}
        lead={summary.facility ? t("dash.centre", { name: summary.facility.name }) : undefined}
        actions={
          <LinkBtn to={paths.watch} tone="primary">
            <Watch size={18} aria-hidden="true" /> Fetch from watch
          </LinkBtn>
        }
      />

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
        <Empty title={t("dash.noReadingsTitle")}>
          <Link to={paths.watch} className="font-semibold text-ink underline">Connect your smartwatch</Link> to see your health score.
        </Empty>
      ) : (
        <section aria-labelledby="score-heading" className="mb-6 grid items-center gap-8 rounded-3xl border border-line bg-surface p-6 md:grid-cols-[280px_1fr] md:p-8">
          <h2 id="score-heading" className="sr-only">Health score</h2>
          <HealthRing factors={factors} active={shown} onHover={setHovered} onPick={pick} />
          <div className="flex flex-col gap-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.06em] text-ink-muted">What makes up your score</p>
              <p className="mt-1 text-sm text-ink-soft">
                From your latest readings ({fmtAgo(newest)}). Point at a part of the ring to see why; click it to chart that vital. A
                prompt to check, not a diagnosis.
              </p>
            </div>
            <ul className="grid gap-2 sm:grid-cols-2">
              {factors.map((f) => (
                <li key={f.key}>
                  <button
                    type="button"
                    onMouseEnter={() => setHovered(f)}
                    onMouseLeave={() => setHovered(null)}
                    onFocus={() => setHovered(f)}
                    onBlur={() => setHovered(null)}
                    onClick={() => pick(f)}
                    className={cx(
                      "flex h-full w-full items-start gap-3 rounded-2xl border p-3 text-left text-sm transition-colors",
                      shown?.key === f.key ? "border-ink bg-paper" : "border-line hover:bg-paper",
                    )}
                  >
                    <span className={cx("mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full", TONE[f.tone].dot)} aria-hidden="true" />
                    <span className="min-w-0 flex-1">
                      <span className="flex justify-between gap-2">
                        <span className="font-medium text-ink">{f.name}</span>
                        <span className="tabular-nums text-ink">{f.value}</span>
                      </span>
                      {(f.tone !== "good" || shown?.key === f.key) && <span className="mt-1 block text-xs text-ink-soft">{f.reason}</span>}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            {summary.next_visit && (
              <Link to={paths.citizenVisits} className="flex flex-wrap items-center gap-2 rounded-2xl bg-lime/50 px-4 py-3 text-sm text-ink hover:bg-lime/70">
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
            title={<span id="detail-heading">{`${vitalLabel(metric.key, metric.label)}, last ${summary.trend_window_days} days`}</span>}
            aside={
              charted.length > 1 && (
                <select
                  aria-label="Vital to look into"
                  value={metric.key}
                  onChange={(e) => setChosen(e.target.value)}
                  className="min-h-10 rounded-full border border-line bg-surface px-4 text-sm"
                >
                  {charted.map((m) => (
                    <option key={m.key} value={m.key}>{vitalLabel(m.key, m.label)}</option>
                  ))}
                </select>
              )
            }
          >
            {series.length > 0 ? (
              <TrendChart metric={metric} points={series.map((p) => ({ measured_at: p.measured_at, value: p.vitals[metric.key], flagged: p.flagged }))} />
            ) : (
              <Empty title={`No readings in the last ${summary.trend_window_days} days`} />
            )}
          </Card>
          <div className="mt-6 grid items-start gap-6 lg:grid-cols-2">
            <Card title="By time of day">
              <TimeOfDay metric={metric} points={series} />
            </Card>
            <Card title="This week against the week before">
              <WeekComparison metric={metric} points={series} />
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
