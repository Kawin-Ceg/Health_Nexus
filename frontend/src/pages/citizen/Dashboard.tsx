import { useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowDown, ArrowRight, ArrowUp, Bell, Bot, Building2, CalendarClock, History, Minus, PlusCircle, ShieldAlert } from "lucide-react";
import { Card, Empty, ErrorNote, LinkBtn, Loading, PageHeader, VisitBadge, cx } from "../../components/app/ui";
import { TrendChart } from "../../components/app/TrendChart";
import { Doodle } from "../../components/landing/Doodle/Doodle";
import { useAuth } from "../../context/AuthContext";
import { fmtAgo, fmtDateTime, fmtVisit, plural } from "../../lib/format";
import { useLabel, useT } from "../../i18n";
import { paths } from "../../lib/routes";
import { useResource } from "../../lib/useResource";
import { getBaselineStatus, getMetrics, getSummary, type Metric, type Summary } from "../../services/health";

type Point = Summary["trend"][number];

const POSITION = {
  below: { label: "Below normal", icon: ArrowDown, cls: "bg-warn-soft text-warn" },
  above: { label: "Above normal", icon: ArrowUp, cls: "bg-warn-soft text-warn" },
  normal: { label: "In range", icon: Minus, cls: "bg-success-soft text-success" },
} as const;

const STAGE = { learning: "Learning", blending: "Getting to know you", personal: "Personal" } as const;

/**
 * Alerts about the same thing repeat the same closing sentence, so five of them
 * read as a wall. Lift whatever trailing sentences they all share into one note
 * shown once, and keep each alert down to what is different about it.
 */
function groupAlerts(messages: string[]): { lines: string[]; shared: string | null } {
  const split = (m: string) => m.split(/(?<=\.)\s+/);
  if (messages.length < 2) return { lines: messages, shared: null };
  const parts = messages.map(split);
  const shared: string[] = [];
  for (let i = 1; i <= Math.min(...parts.map((p) => p.length)) - 1; i += 1) {
    const tail = parts[0][parts[0].length - i];
    if (parts.every((p) => p[p.length - i] === tail)) shared.unshift(tail);
    else break;
  }
  if (shared.length === 0) return { lines: messages, shared: null };
  return {
    lines: parts.map((p) => p.slice(0, p.length - shared.length).join(" ")),
    shared: shared.join(" "),
  };
}

/** A tiny line of one vital's readings, with its normal range shaded. */
function Sparkline({ values, metric }: { values: number[]; metric: Metric }) {
  if (values.length < 2) return <div className="h-10" aria-hidden="true" />;
  const lo = Math.min(...values, metric.normal?.[0] ?? Infinity);
  const hi = Math.max(...values, metric.normal?.[1] ?? -Infinity);
  const span = hi - lo || 1;
  const y = (v: number) => 36 - ((v - lo) / span) * 32;
  const x = (i: number) => (i / (values.length - 1)) * 100;
  const line = values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  return (
    <svg viewBox="0 0 100 40" preserveAspectRatio="none" className="h-10 w-full" aria-hidden="true">
      {metric.normal && (
        <rect x="0" y={y(metric.normal[1])} width="100" height={Math.max(1, y(metric.normal[0]) - y(metric.normal[1]))} className="fill-success-soft" />
      )}
      <polyline points={line} fill="none" className="stroke-ink" strokeWidth="1.5" vectorEffect="non-scaling-stroke" strokeLinejoin="round" />
      <circle cx={x(values.length - 1)} cy={y(values[values.length - 1])} r="2.5" className="fill-ink" />
    </svg>
  );
}

/** How far a vital has come towards a fully personal baseline. */
function BaselineRing({ readings, full, stage }: { readings: number; full: number; stage: keyof typeof STAGE }) {
  const r = 14;
  const c = 2 * Math.PI * r;
  const done = Math.min(1, readings / full);
  return (
    <span className="relative inline-grid h-9 w-9 shrink-0 place-items-center" title={`${STAGE[stage]}: ${Math.min(readings, full)} of ${full} readings`}>
      <svg viewBox="0 0 36 36" className="absolute inset-0 -rotate-90" aria-hidden="true">
        <circle cx="18" cy="18" r={r} fill="none" strokeWidth="3" className="stroke-paper-raised" />
        <circle
          cx="18"
          cy="18"
          r={r}
          fill="none"
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray={`${c * done} ${c}`}
          className={stage === "personal" ? "stroke-success" : "stroke-olive"}
        />
      </svg>
      <span className="text-[10px] font-semibold tabular-nums text-ink-soft" aria-hidden="true">
        {Math.round(done * 100)}%
      </span>
      <span className="visually-hidden">
        {STAGE[stage]}: {Math.min(readings, full)} of {full} readings towards your personal baseline.
      </span>
    </span>
  );
}

const SLOTS = [
  { id: "morning", label: "Morning", hours: "5 am to noon", test: (h: number) => h >= 5 && h < 12 },
  { id: "afternoon", label: "Afternoon", hours: "noon to 5 pm", test: (h: number) => h >= 12 && h < 17 },
  { id: "evening", label: "Evening", hours: "5 pm to 10 pm", test: (h: number) => h >= 17 && h < 22 },
  { id: "night", label: "Night", hours: "10 pm to 5 am", test: (h: number) => h >= 22 || h < 5 },
] as const;

const hourOf = (iso: string) =>
  Number(new Intl.DateTimeFormat("en-IN", { timeZone: "Asia/Kolkata", hour: "numeric", hourCycle: "h23" }).format(new Date(iso)));

const mean = (xs: number[]) => xs.reduce((a, b) => a + b, 0) / xs.length;

/** Average of one vital by time of day, against its normal range. */
function TimeOfDay({ metric, points }: { metric: Metric; points: Point[] }) {
  const rows = SLOTS.map((s) => {
    const values = points.filter((p) => s.test(hourOf(p.measured_at))).map((p) => p.vitals[metric.key]);
    return { ...s, n: values.length, avg: values.length ? mean(values) : null };
  });
  const present = rows.flatMap((r) => (r.avg === null ? [] : [{ ...r, avg: r.avg }]));
  if (present.length === 0) return <p className="text-sm text-ink-soft">No readings in the last 30 days.</p>;
  const lo = Math.min(...present.map((r) => r.avg), metric.normal?.[0] ?? Infinity);
  const hi = Math.max(...present.map((r) => r.avg), metric.normal?.[1] ?? -Infinity);
  const pad = (hi - lo) * 0.15 || 1;
  const pct = (v: number) => ((v - (lo - pad)) / (hi - lo + 2 * pad)) * 100;
  const top = present.reduce((a, b) => (b.avg > a.avg ? b : a));
  const low = present.reduce((a, b) => (b.avg < a.avg ? b : a));
  const diff = top.avg - low.avg;
  return (
    <div>
      <p className="mb-4 text-sm text-ink-soft">
        {present.length < 2
          ? `All your ${metric.label.toLowerCase()} readings were taken in the ${present[0].label.toLowerCase()}. Log at other times to compare.`
          : diff < 10 ** -metric.decimals
            ? "About the same at every time of day."
            : `Usually highest in the ${top.label.toLowerCase()}, ${diff.toFixed(metric.decimals)} ${metric.unit} above the ${low.label.toLowerCase()}.`}
      </p>
      <ul className="flex flex-col gap-3">
        {rows.map((r) => (
          <li key={r.id} className="grid grid-cols-[88px_1fr_auto] items-center gap-3 text-sm">
            <span>
              <span className="block font-medium text-ink">{r.label}</span>
              <span className="block text-xs text-ink-muted">{r.hours}</span>
            </span>
            <span className="relative h-7 rounded-full bg-paper">
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
                    "absolute top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-surface",
                    metric.normal && (r.avg < metric.normal[0] || r.avg > metric.normal[1]) ? "bg-warn" : "bg-ink",
                  )}
                  style={{ left: `${pct(r.avg)}%` }}
                  aria-hidden="true"
                />
              )}
            </span>
            <span className="w-28 text-right tabular-nums">
              {r.avg === null ? (
                <span className="text-ink-muted">No readings</span>
              ) : (
                <>
                  <span className="font-display text-lg text-ink">{r.avg.toFixed(metric.decimals)}</span>{" "}
                  <span className="text-xs text-ink-muted">({r.n})</span>
                </>
              )}
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-3 flex flex-wrap items-center gap-2 text-xs text-ink-muted">
        {metric.normal && (
          <>
            <span className="h-3 w-6 rounded-full bg-success-soft" aria-hidden="true" /> Normal {metric.normal[0]}–{metric.normal[1]} {metric.unit} ·
          </>
        )}{" "}
        averages over the last 30 days, (n) readings
      </p>
    </div>
  );
}

/** Share of readings below, in and above the normal range. */
function RangeShare({ metric, points }: { metric: Metric; points: Point[] }) {
  if (!metric.normal) return <p className="text-sm text-ink-soft">{metric.label} has no normal range; it is tracked for your record.</p>;
  if (points.length === 0) return <p className="text-sm text-ink-soft">No readings in the last 30 days.</p>;
  const [lo, hi] = metric.normal;
  const below = points.filter((p) => p.vitals[metric.key] < lo).length;
  const above = points.filter((p) => p.vitals[metric.key] > hi).length;
  const within = points.length - below - above;
  const parts = [
    { label: "In range", n: within, cls: "stroke-success", dot: "bg-success" },
    { label: "Above", n: above, cls: "stroke-warn", dot: "bg-warn" },
    { label: "Below", n: below, cls: "stroke-info", dot: "bg-info" },
  ];
  const r = 42;
  const c = 2 * Math.PI * r;
  const segments = parts.reduce<{ offset: number; arcs: { label: string; cls: string; len: number; at: number }[] }>(
    (acc, p) => {
      const len = (p.n / points.length) * c;
      return { offset: acc.offset + len, arcs: p.n ? [...acc.arcs, { label: p.label, cls: p.cls, len, at: acc.offset }] : acc.arcs };
    },
    { offset: 0, arcs: [] },
  ).arcs;
  return (
    <div className="flex items-center gap-5">
      <span className="relative grid h-28 w-28 shrink-0 place-items-center">
        <svg viewBox="0 0 100 100" className="absolute inset-0 -rotate-90" aria-hidden="true">
          <circle cx="50" cy="50" r={r} fill="none" strokeWidth="12" className="stroke-paper-raised" />
          {segments.map((s) => (
            <circle key={s.label} cx="50" cy="50" r={r} fill="none" strokeWidth="12" className={s.cls} strokeDasharray={`${s.len} ${c}`} strokeDashoffset={-s.at} />
          ))}
        </svg>
        <span className="text-center">
          <span className="block font-display text-2xl leading-none text-ink">{Math.round((within / points.length) * 100)}%</span>
          <span className="text-[11px] text-ink-muted">in range</span>
        </span>
      </span>
      <ul className="flex flex-col gap-2 text-sm">
        {parts.map((p) => (
          <li key={p.label} className="flex items-center gap-2">
            <span className={cx("h-2.5 w-2.5 rounded-full", p.dot)} aria-hidden="true" />
            <span className="text-ink">{p.label}</span>
            <span className="tabular-nums text-ink-muted">{p.n}</span>
          </li>
        ))}
        <li className="text-xs text-ink-muted">of {plural(points.length, "reading")}, last 30 days</li>
      </ul>
    </div>
  );
}

/** Average this week against the week before. */
function WeekOnWeek({ metric, points }: { metric: Metric; points: Point[] }) {
  const now = Date.now();
  const age = (p: Point) => (now - new Date(p.measured_at).getTime()) / 86400_000;
  const thisWeek = points.filter((p) => age(p) < 7).map((p) => p.vitals[metric.key]);
  const lastWeek = points.filter((p) => age(p) >= 7 && age(p) < 14).map((p) => p.vitals[metric.key]);
  if (!thisWeek.length || !lastWeek.length) {
    return <p className="text-sm text-ink-soft">Log {metric.label.toLowerCase()} in two weeks running to see how it is moving.</p>;
  }
  const a = mean(thisWeek);
  const b = mean(lastWeek);
  const delta = a - b;
  const steady = Math.abs(delta) < 10 ** -metric.decimals;
  const Icon = steady ? Minus : delta > 0 ? ArrowUp : ArrowDown;
  return (
    <div>
      <p className="flex items-baseline gap-2">
        <Icon size={20} className="self-center text-ink" aria-hidden="true" />
        <span className="font-display text-4xl tabular-nums text-ink">
          {steady ? "Steady" : `${delta > 0 ? "+" : ""}${delta.toFixed(metric.decimals)}`}
        </span>
        {!steady && <span className="text-sm text-ink-soft">{metric.unit}</span>}
      </p>
      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div className="rounded-2xl bg-paper p-3">
          <dt className="text-xs text-ink-muted">This week</dt>
          <dd className="font-display text-xl tabular-nums text-ink">{a.toFixed(metric.decimals)}</dd>
          <dd className="text-xs text-ink-muted">{plural(thisWeek.length, "reading")}</dd>
        </div>
        <div className="rounded-2xl bg-paper p-3">
          <dt className="text-xs text-ink-muted">Week before</dt>
          <dd className="font-display text-xl tabular-nums text-ink">{b.toFixed(metric.decimals)}</dd>
          <dd className="text-xs text-ink-muted">{plural(lastWeek.length, "reading")}</dd>
        </div>
      </dl>
    </div>
  );
}

/** One card per other page: what is there now, and a way in. */
function Gist({ to, icon: Icon, title, children }: { to: string; icon: typeof Bell; title: string; children: ReactNode }) {
  return (
    <Link
      to={to}
      className="group flex flex-col rounded-3xl border border-line bg-surface p-5 transition-[border-color,box-shadow] duration-300 hover:border-ink/30 hover:shadow-[0_0_40px_rgb(var(--hn-glow))]"
    >
      <span className="flex items-center justify-between">
        <span className="grid h-10 w-10 place-items-center rounded-full bg-lime text-olive">
          <Icon size={18} aria-hidden="true" />
        </span>
        <ArrowRight size={18} className="text-ink-muted transition-transform group-hover:translate-x-1" aria-hidden="true" />
      </span>
      <span className="mt-4 font-display text-xl text-ink">{title}</span>
      <span className="mt-1 text-sm text-ink-soft">{children}</span>
    </Link>
  );
}

export function CitizenDashboard() {
  const { user } = useAuth();
  const t = useT();
  const label = useLabel();
  const { data, error, loading, reload } = useResource(
    (signal) => Promise.all([getSummary(signal), getMetrics(), getBaselineStatus(signal)]),
    "summary",
  );
  const [chosen, setChosen] = useState<string | null>(null);

  const [summary, info, baselines] = data ?? [null, null, null];
  const metrics = useMemo(() => new Map((info?.metrics ?? []).map((m) => [m.key, m])), [info]);
  const baselineBy = useMemo(() => new Map((baselines?.vitals ?? []).map((v) => [v.key, v])), [baselines]);

  if (loading && !data) return <Loading label="Loading your dashboard" />;
  if (error || !summary || !info) return <ErrorNote message={error ?? "Could not load your dashboard."} onRetry={reload} />;

  const unreviewed = !summary.facility || summary.facility.workers_assigned === 0;
  const offNormal = summary.latest.filter((v) => v.position !== "normal");
  const alerts = groupAlerts(summary.alerts.map((a) => a.message));
  const seriesOf = (key: string) => summary.trend.filter((p) => p.vitals[key] !== undefined);
  const tiles = summary.latest.filter((v) => metrics.has(v.key));
  const charted = (info.metrics ?? []).filter((m) => summary.trend.some((p) => p.vitals[m.key] !== undefined));
  const metric = metrics.get(chosen ?? "") ?? metrics.get(offNormal[0]?.key ?? "") ?? charted[0];
  const points = metric
    ? seriesOf(metric.key).map((p) => ({ measured_at: p.measured_at, value: p.vitals[metric.key], flagged: p.flagged }))
    : [];
  const pick = (key: string, scroll = true) => {
    setChosen(key);
    if (scroll) document.getElementById("vital-chart")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };
  const newest = summary.latest.reduce<string | null>((acc, v) => (!acc || v.measured_at > acc ? v.measured_at : acc), null);
  const personal = baselines ? baselines.vitals.filter((v) => v.stage === "personal").length : 0;

  return (
    <>
      <PageHeader
        title={t("dash.hello", { name: user?.name.split(" ")[0] ?? "" })}
        lead={summary.facility ? t("dash.centre", { name: summary.facility.name }) : undefined}
        actions={
          <LinkBtn to={paths.submitVitals} tone="primary">
            <PlusCircle size={18} aria-hidden="true" /> {t("dash.log")}
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

      <section className="relative isolate mb-4 overflow-clip rounded-3xl border border-line bg-surface p-6 md:p-8" aria-labelledby="standing">
        <Doodle piece="ecg" className="-right-6 -bottom-10 w-56 rotate-[6deg] [--doodle-opacity:0.9]" />
        <h2 id="standing" className="sr-only">
          Where you stand
        </h2>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-64 flex-1">
            <p className={cx("flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.06em]", offNormal.length ? "text-warn" : "text-success")}>
              {offNormal.length ? <ArrowUp size={16} aria-hidden="true" /> : <Minus size={16} aria-hidden="true" />}
              {offNormal.length ? t("dash.worth") : summary.latest.length ? t("dash.steady") : t("dash.starting")}
            </p>
            <p className="mt-2 max-w-xl font-display text-2xl leading-snug text-ink md:text-3xl">
              {offNormal.length
                ? t("dash.outside", { n: offNormal.length })
                : summary.latest.length
                  ? t("dash.allUsual")
                  : t("dash.noReadings")}
            </p>
            <p className="mt-2 max-w-xl text-sm text-ink-soft">
              {offNormal.length > 0
                ? offNormal.map((v) => label("vital", v.key, metrics.get(v.key)?.label)).join(", ")
                : t("dash.week", { n: summary.readings_last_7_days })}
              {summary.open_flags > 0 && summary.facility ? t("dash.flaggedSent", { centre: summary.facility.name, n: summary.open_flags }) : ""}
            </p>
          </div>
          {summary.next_visit && (
            <div className="rounded-2xl bg-lime/60 px-5 py-4 text-sm lg:mr-40">
              <p className="flex items-center gap-2 font-semibold text-ink">
                <CalendarClock size={16} aria-hidden="true" />
                {fmtVisit(summary.next_visit.scheduled_for)}
              </p>
              <p className="text-ink-soft">{summary.next_visit.worker_name ? t("dash.with", { name: summary.next_visit.worker_name }) : t("dash.homeVisit")}</p>
              <div className="mt-2">
                <VisitBadge state={summary.next_visit.state} />
              </div>
            </div>
          )}
        </div>
      </section>

      <nav aria-label="Quick actions" className="mb-8 flex flex-wrap gap-2">
        <LinkBtn to={paths.submitVitals}>
          <PlusCircle size={16} aria-hidden="true" /> {t("dash.quick.log")}
        </LinkBtn>
        <LinkBtn to={paths.assistant}>
          <Bot size={16} aria-hidden="true" /> {t("dash.quick.ask")}
        </LinkBtn>
        <LinkBtn to={paths.history}>
          <History size={16} aria-hidden="true" /> {t("dash.quick.history")}
        </LinkBtn>
        <LinkBtn to={paths.citizenAlerts}>
          <Bell size={16} aria-hidden="true" /> {t("dash.quick.alerts")}
        </LinkBtn>
      </nav>

      <section aria-labelledby="vitals-heading" className="mb-8">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
          <h2 id="vitals-heading" className="text-2xl text-ink">
            {t("dash.vitals")}
          </h2>
          {baselines && (
            <p className="text-sm text-ink-soft">
              {personal} of {baselines.vitals.length} judged against your own normal. Each ring fills over {baselines.full_readings} readings.
            </p>
          )}
        </div>
        {tiles.length === 0 ? (
          <Empty title={t("dash.noReadingsTitle")}>
            <Link to={paths.submitVitals} className="font-semibold text-ink underline">
              {t("dash.firstReading")}
            </Link>{" "}
            to see each vital here.
          </Empty>
        ) : (
          <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {tiles.map((v) => {
              const m = metrics.get(v.key);
              if (!m) return null;
              const pos = POSITION[v.position];
              const b = baselineBy.get(v.key);
              return (
                <li key={v.key}>
                  <button
                    type="button"
                    onClick={() => pick(v.key)}
                    aria-pressed={metric?.key === v.key}
                    aria-controls="vital-chart"
                    className={cx(
                      "flex h-full w-full flex-col rounded-3xl border-2 bg-surface p-4 text-left transition-[border-color,box-shadow] duration-300 hover:shadow-[0_0_40px_rgb(var(--hn-glow))]",
                      metric?.key === v.key ? "border-ink" : v.position !== "normal" ? "border-warn/50" : "border-line",
                    )}
                  >
                    <span className="flex items-start justify-between gap-2">
                      <span className="text-sm font-medium text-ink-soft">{m.label}</span>
                      {b && baselines && <BaselineRing readings={b.readings} full={baselines.full_readings} stage={b.stage} />}
                    </span>
                    <span className="mt-1 font-display text-3xl tabular-nums leading-none text-ink">
                      {v.value.toFixed(m.decimals)} <span className="font-sans text-sm text-ink-soft">{m.unit}</span>
                    </span>
                    <span className="mt-3">
                      <Sparkline values={seriesOf(v.key).map((p) => p.vitals[v.key])} metric={m} />
                    </span>
                    <span className="mt-2 flex items-center justify-between gap-2 text-xs">
                      {m.normal ? (
                        <span className={cx("inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-semibold", pos.cls)}>
                          <pos.icon size={12} aria-hidden="true" /> {pos.label}
                        </span>
                      ) : (
                        <span className="text-ink-muted">No normal range</span>
                      )}
                      <span className="text-ink-muted">{fmtAgo(v.measured_at)}</span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <div id="vital-chart" className="mb-6 grid scroll-mt-6 items-start gap-6 lg:grid-cols-3">
        <Card
          className="scroll-mt-6 lg:col-span-2"
          title={metric ? `${metric.label}, last ${summary.trend_window_days} days` : "Trend"}
          aside={
            charted.length > 1 && (
              <select
                aria-label="Measurement to chart"
                value={metric?.key}
                onChange={(e) => pick(e.target.value, false)}
                className="min-h-10 rounded-full border border-line bg-surface px-4 text-sm"
              >
                {charted.map((m) => (
                  <option key={m.key} value={m.key}>
                    {m.label}
                  </option>
                ))}
              </select>
            )
          }
        >
          {metric && points.length > 0 ? (
            <TrendChart metric={metric} points={points} />
          ) : (
            <Empty title={`No readings in the last ${summary.trend_window_days} days`} />
          )}
        </Card>

        <div className="flex flex-col gap-6">
          <Card title="This week">
            <dl className="grid grid-cols-3 gap-3 text-center">
              <div className="rounded-2xl bg-paper p-3">
                <dt className="text-xs text-ink-muted">Readings</dt>
                <dd className="font-display text-3xl tabular-nums text-ink">{summary.readings_last_7_days}</dd>
              </div>
              <div className="rounded-2xl bg-paper p-3">
                <dt className="text-xs text-ink-muted">Open flags</dt>
                <dd className={cx("font-display text-3xl tabular-nums", summary.open_flags ? "text-warn" : "text-ink")}>{summary.open_flags}</dd>
              </div>
              <div className="rounded-2xl bg-paper p-3">
                <dt className="text-xs text-ink-muted">Unread</dt>
                <dd className="font-display text-3xl tabular-nums text-ink">{summary.unread_alerts}</dd>
              </div>
            </dl>
          </Card>
          <Card
            title="Latest alerts"
            aside={
              <Link to={paths.citizenAlerts} className="text-sm font-semibold text-ink underline underline-offset-4">
                See all
              </Link>
            }
          >
            {summary.alerts.length === 0 ? (
              <p className="text-sm text-ink-soft">Nothing new.</p>
            ) : (
              <>
                <ul className="flex flex-col gap-3">
                  {summary.alerts.slice(0, 3).map((a, i) => (
                    <li key={a.id} className="text-sm">
                      <p className="text-ink">{alerts.lines[i] ?? a.message}</p>
                      <p className="text-xs text-ink-soft">{fmtDateTime(a.created_at)}</p>
                    </li>
                  ))}
                </ul>
                {alerts.shared && <p className="mt-3 border-t border-line pt-3 text-xs text-ink-soft">{alerts.shared}</p>}
              </>
            )}
          </Card>
        </div>
      </div>

      {metric && (
        <section aria-labelledby="patterns-heading" className="mb-8">
          <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
            <h2 id="patterns-heading" className="text-2xl text-ink">
              Patterns in your {metric.label.toLowerCase()}
            </h2>
            <p className="text-sm text-ink-soft">Pick a vital above, or change it in the chart, to see its patterns.</p>
          </div>
          <div className="grid items-start gap-6 lg:grid-cols-3">
            <Card title="Time of day">
              <TimeOfDay metric={metric} points={seriesOf(metric.key)} />
            </Card>
            <Card title="In your normal range">
              <RangeShare metric={metric} points={seriesOf(metric.key)} />
            </Card>
            <Card title="This week vs last">
              <WeekOnWeek metric={metric} points={seriesOf(metric.key)} />
            </Card>
          </div>
        </section>
      )}

      <section aria-labelledby="around-heading">
        <h2 id="around-heading" className="mb-4 text-2xl text-ink">
          {t("dash.around")}
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Gist to={paths.history} icon={History} title={t("nav.history")}>
            {summary.readings_total ? t("dash.history", { n: summary.readings_total, ago: fmtAgo(newest) }) : t("dash.historyNone")}
          </Gist>
          <Gist to={paths.citizenAlerts} icon={Bell} title={t("nav.alerts")}>
            {summary.next_visit
              ? t("dash.alertsVisit", { when: fmtVisit(summary.next_visit.scheduled_for), n: summary.unread_alerts })
              : t("dash.alertsNone", { n: summary.unread_alerts })}
          </Gist>
          <Gist to={paths.assistant} icon={Bot} title={t("dash.askTitle")}>
            {t("dash.askBody")}
          </Gist>
          <Gist to={`${paths.settings}?tab=centre`} icon={Building2} title={t("dash.centreTitle")}>
            {summary.facility
              ? t("dash.centreBody", { name: summary.facility.name, district: summary.facility.district, n: summary.facility.workers_assigned })
              : t("dash.centreNone")}
          </Gist>
        </div>
      </section>
    </>
  );
}
