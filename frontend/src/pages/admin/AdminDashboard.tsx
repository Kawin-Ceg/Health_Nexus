import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { Activity, AlertTriangle, CalendarCheck, CalendarPlus, CalendarX, Flag, Gauge, Megaphone, Stethoscope, Users, ArrowRight, BadgeCheck, Building2, ClipboardList, Clock, Hourglass, Inbox, MessageSquareText, TrendingDown, TrendingUp, UserX } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Donut, type Slice } from "../../components/app/Donut";
import { Btn, Card, ErrorNote, Loading, cx, inputCls } from "../../components/app/ui";
import { fmtAgo } from "../../lib/format";
import { paths } from "../../lib/routes";
import { useResource } from "../../lib/useResource";
import { errorMessage } from "../../services/api";
import { downloadResearchExport, getCentreActivity, getCentres, getOverview, type Overview } from "../../services/admin";

function ResearchExport() {
  const [days, setDays] = useState(365);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const download = async () => {
    setBusy(true);
    setErr(null);
    try {
      await downloadResearchExport(days);
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title="Research data">
      <p className="text-sm text-ink-soft">
        A CSV of readings from citizens who turned on research use, and nobody else. It has no names, contact details,
        exact ages, areas or times, and each person gets a code that changes with every download. Each download is
        written to the audit trail.
      </p>
      <div className="mt-4 flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-sm text-ink">
          Readings from the last
          <select value={days} onChange={(e) => setDays(Number(e.target.value))} className={inputCls}>
            <option value={90}>90 days</option>
            <option value={365}>year</option>
            <option value={1825}>5 years</option>
          </select>
        </label>
        <Btn busy={busy} onClick={() => void download()}>
          Download CSV
        </Btn>
      </div>
      {err && <p className="mt-2 text-sm text-danger">{err}</p>}
    </Card>
  );
}

type Tone = "ok" | "warn" | "bad";
const TONE: Record<Tone, { label: string; pill: string; dot: string }> = {
  ok: { label: "No action needed", pill: "bg-green-50 text-green-800", dot: "bg-green-500" },
  warn: { label: "Needs attention", pill: "bg-amber-50 text-amber-800", dot: "bg-amber-400" },
  bad: { label: "Act now", pill: "bg-red-50 text-red-800", dot: "bg-red-500" },
};

interface SubStat {
  icon: typeof BadgeCheck;
  label: string;
  value: ReactNode;
}

function ActionCard({ icon: Icon, title, value, sub, tone, stats, slices, to, cta, children }: {
  icon: typeof BadgeCheck;
  title: string;
  value: number;
  sub: string;
  tone: Tone;
  stats: [SubStat, SubStat];
  slices: Slice[];
  to: string;
  cta: string;
  children?: ReactNode;
}) {
  return (
    <section className="flex flex-col rounded-3xl border border-line bg-surface p-5">
      <div className="flex items-start justify-between gap-3">
        <span className="grid h-11 w-11 place-items-center rounded-xl border border-line bg-paper text-ink">
          <Icon size={20} aria-hidden="true" />
        </span>
        <span className={cx("inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold", TONE[tone].pill)}>
          {TONE[tone].label}
        </span>
      </div>
      <div className="mt-3 flex items-center justify-between gap-4">
        <div className="min-w-0">
          <h2 className="font-sans text-lg font-semibold text-ink">{title}</h2>
          <p className="text-4xl font-bold tabular-nums leading-tight text-ink">{value}</p>
          <p className="text-sm text-ink-soft">{sub}</p>
        </div>
        <Donut slices={slices} caption={title} size={76} />
      </div>
      {children}
      <div className="mt-4 grid grid-cols-2 border-t border-line pt-4">
        {stats.map((s, i) => (
          <div key={s.label} className={cx("flex items-center gap-3", i === 1 && "border-l border-line pl-4")}>
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-paper-raised text-ink-soft">
              <s.icon size={16} aria-hidden="true" />
            </span>
            <span className="min-w-0">
              <span className="block text-xs text-ink-muted">{s.label}</span>
              <span className="block font-semibold tabular-nums text-ink">{s.value}</span>
            </span>
          </div>
        ))}
      </div>
      <Link to={to} className="mt-auto inline-flex items-center gap-1 pt-4 text-sm font-semibold text-ink">
        {cta} <ArrowRight size={14} aria-hidden="true" />
      </Link>
    </section>
  );
}

function Bars({ values, color }: { values: number[]; color: string }) {
  const max = Math.max(1, ...values);
  return (
    <div className="flex h-10 items-end gap-1" aria-hidden="true">
      {values.map((v, i) => (
        <span
          key={i}
          className="flex-1 rounded-sm"
          style={{ height: `${Math.max(6, (v / max) * 100)}%`, background: color, opacity: i === values.length - 1 ? 1 : 0.45 }}
        />
      ))}
    </div>
  );
}

function Metric({ label, values, color }: { label: string; values: number[]; color: string }) {
  const now = values[values.length - 1] ?? 0;
  const before = values[values.length - 2] ?? 0;
  const delta = now - before;
  const Trend = delta >= 0 ? TrendingUp : TrendingDown;
  return (
    <li className="rounded-2xl border border-line p-4">
      <p className="text-sm text-ink-soft">{label}</p>
      <div className="mt-1 flex flex-wrap items-baseline justify-between gap-2">
        <span className="text-2xl font-semibold tabular-nums text-ink">{now}</span>
        <span className={cx("inline-flex items-center gap-1 text-xs font-medium", delta === 0 ? "text-ink-muted" : delta > 0 ? "text-green-700" : "text-red-700")}>
          {delta !== 0 && <Trend size={14} aria-hidden="true" />}
          {delta === 0 ? "same as last week" : `${delta > 0 ? "+" : ""}${delta} vs last week`}
        </span>
      </div>
      <div className="mt-3">
        <Bars values={values} color={color} />
      </div>
    </li>
  );
}

function ActivityCard({ title, data, color }: { title: string; data: Record<string, number[]>; color: string }) {
  return (
    <Card title={title}>
      <p className="-mt-2 mb-4 text-xs text-ink-muted">This week, with the 7 weeks before it.</p>
      <ul className="grid gap-3 sm:grid-cols-2">
        {Object.entries(data).map(([label, values]) => (
          <Metric key={label} label={label} values={values} color={color} />
        ))}
      </ul>
    </Card>
  );
}

const CARD = "rounded-xl border border-line bg-surface";
const LABEL = "text-[13px] text-ink-muted";

function Dot({ tone }: { tone: "red" | "amber" | "grey" | "green" }) {
  const cls = { red: "bg-red-600", amber: "bg-amber-500", grey: "bg-ink-muted/60", green: "bg-green-600" }[tone];
  return <span className={cx("inline-block h-1.5 w-1.5 shrink-0 rounded-full", cls)} aria-hidden="true" />;
}

/** Largest-remainder rounding: percentages that always sum to 100. */
function shares(values: number[]): number[] {
  const total = values.reduce((a, b) => a + b, 0);
  if (!total) return values.map(() => 0);
  const raw = values.map((v) => (v / total) * 100);
  const floor = raw.map(Math.floor);
  let left = 100 - floor.reduce((a, b) => a + b, 0);
  raw.map((r, i) => [r - floor[i], i] as const).sort((a, b) => b[0] - a[0]).forEach(([, i]) => {
    if (left > 0) {
      floor[i] += 1;
      left -= 1;
    }
  });
  return floor;
}

const ROLE_SHADES = ["#2f7d6d", "#d19a1b", "#7a5bbf"];

function AccountsCard({ o }: { o: Overview }) {
  const [active, setActive] = useState<number | null>(null);
  const [drawn, setDrawn] = useState(reduced());
  useEffect(() => {
    if (drawn) return;
    const id = requestAnimationFrame(() => setDrawn(true));
    return () => cancelAnimationFrame(id);
  }, [drawn]);
  const roles = [
    { label: "Citizens", value: o.users_by_role.user },
    { label: "PHC workers", value: o.users_by_role.phc_worker },
    { label: "Administrators", value: o.users_by_role.admin },
  ];
  const attention = [
    { label: "Awaiting approval", value: o.users_by_role.pending_phc, to: `${paths.adminApplications}` },
    { label: "Deactivated", value: o.inactive_accounts, to: `${paths.adminAccounts}?status=inactive` },
    { label: "Email not confirmed", value: o.unverified_accounts, to: `${paths.adminAccounts}?status=unverified` },
  ];
  const total = roles.reduce((a, r) => a + r.value, 0);
  const pct = shares(roles.map((r) => r.value));

  const R = 80;
  const C = 2 * Math.PI * R;
  const gap = (2 / 360) * C;
  const minArc = (2 / 360) * C;
  let at = 0;
  const arcs = roles.map((r, i) => {
    const len = total ? Math.max(minArc, (r.value / total) * C) : 0;
    const arc = { i, start: at, len: Math.max(0, len - gap) };
    at += len;
    return arc;
  });
  const summary = [...roles, ...attention].map((x) => `${x.label} ${x.value}`).join(", ");

  return (
    <Card title="Accounts">
      <div className="mx-auto w-60" role="img" aria-label={`${total} accounts. ${summary}.`}>
        <div className="relative">
          <svg viewBox="0 0 200 200" className="h-60 w-60 -rotate-90">
            <circle cx="100" cy="100" r={R} fill="none" strokeWidth="26" className="stroke-paper-raised" />
            {arcs.map((a) =>
              a.len > 0 ? (
                <circle
                  key={a.i}
                  cx="100"
                  cy="100"
                  r={R}
                  fill="none"
                  stroke={ROLE_SHADES[a.i]}
                  strokeWidth="26"
                  strokeDasharray={`${drawn ? a.len : 0} ${C}`}
                  strokeDashoffset={-a.start}
                  opacity={active !== null && active !== a.i ? 0.4 : 1}
                  onMouseEnter={() => setActive(a.i)}
                  onMouseLeave={() => setActive(null)}
                  className="cursor-pointer motion-safe:transition-[stroke-dasharray,opacity] motion-safe:duration-700"
                >
                  <title>{`${roles[a.i].label}: ${roles[a.i].value} (${pct[a.i]}%)`}</title>
                </circle>
              ) : null,
            )}
          </svg>
          <div className="pointer-events-none absolute inset-0 grid place-items-center text-center">
            <div>
              <p className="text-4xl font-semibold tabular-nums text-ink">{active === null ? total : roles[active].value}</p>
              <p className="text-xs text-ink-muted">{active === null ? "accounts" : `${roles[active].label} · ${pct[active]}%`}</p>
            </div>
          </div>
        </div>
      </div>
      <div className="mt-6 grid gap-x-6 gap-y-6 sm:grid-cols-2">
        <div>
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-muted">Roles</p>
          <ul className="flex flex-col gap-3">
            {roles.map((r, i) => (
              <li
                key={r.label}
                tabIndex={0}
                onMouseEnter={() => setActive(i)}
                onMouseLeave={() => setActive(null)}
                onFocus={() => setActive(i)}
                onBlur={() => setActive(null)}
                className={cx("rounded-xl border p-3 outline-none focus-visible:ring-2 focus-visible:ring-ink", active === i ? "border-ink" : "border-line")}
              >
                <p className="flex items-center gap-2 text-[13px] text-ink">
                  <span className="h-2 w-2 rounded-full" style={{ background: ROLE_SHADES[i] }} aria-hidden="true" />
                  {r.label}
                </p>
                <p className="mt-1 flex items-baseline gap-2">
                  <span className="text-2xl font-semibold tabular-nums text-ink">{r.value}</span>
                  <span className="text-[13px] text-ink-muted">{pct[i]}%</span>
                </p>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-muted">Needs attention</p>
          <ul className="flex flex-col gap-3">
            {attention.map((x) => {
              const body = (
                <>
                  <p className="flex items-center gap-2 text-[13px] text-ink">
                    <Dot tone={x.value > 0 ? "amber" : "grey"} />
                    {x.label}
                  </p>
                  <p className={cx("mt-1 text-2xl font-semibold tabular-nums", x.value > 0 ? "text-ink" : "text-ink-muted")}>{x.value}</p>
                </>
              );
              return (
                <li key={x.label}>
                  {x.value > 0 ? (
                    <Link to={x.to} className="block rounded-xl border border-line p-3 hover:border-amber-400 focus-visible:outline-2 focus-visible:outline-ink">
                      {body}
                    </Link>
                  ) : (
                    <div className="rounded-xl border border-line p-3 opacity-70">{body}</div>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </Card>
  );
}

function reduced() {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

const weekLabel = (iso: string) => new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short" });

function delta(now: number, before: number, show: boolean) {
  if (!show) return null;
  const d = now - before;
  return d === 0 ? "Same as previous period" : `${d > 0 ? "+" : ""}${d} vs previous period`;
}

function CentreActivityCard() {
  const [centre, setCentre] = useState("");
  const [query, setQuery] = useState("");
  const [days, setDays] = useState(30);
  const centres = useResource((s) => getCentres({ state: "active", limit: 200 }, s).then((r) => r.items), "dash-centres");
  useEffect(() => {
    if (!centre && centres.data?.length) setCentre(centres.data[0].id);
  }, [centre, centres.data]);
  const stats = useResource((s) => (centre ? getCentreActivity(centre, days, s) : Promise.resolve(null)), `activity-${centre}-${days}`);
  const a = stats.data;
  const list = centres.data ?? [];
  const searchable = list.length > 8;
  const shown = query ? list.filter((c) => c.name.toLowerCase().includes(query.toLowerCase())) : list;

  const cur = a?.current;
  const prev = a?.previous;
  const showDelta = !!prev?.has_data;
  const rate = cur && cur.scheduled ? `${Math.round((cur.done / cur.scheduled) * 100)}%` : "—";
  const tiles: { label: string; value: ReactNode; sub?: string | null; tone?: string; icon: typeof CalendarPlus; chip: string }[] = a && cur && prev
    ? [
        { label: "Visits scheduled", value: cur.scheduled, sub: delta(cur.scheduled, prev.scheduled, showDelta), icon: CalendarPlus, chip: "bg-sky-50 text-sky-700" },
        { label: "Visits done", value: cur.done, sub: delta(cur.done, prev.done, showDelta), icon: CalendarCheck, chip: "bg-green-50 text-green-700" },
        { label: "Visits missed", value: cur.missed, sub: delta(cur.missed, prev.missed, showDelta), icon: CalendarX, chip: "bg-amber-50 text-amber-700" },
        { label: "Completion rate", value: rate, sub: cur.scheduled ? `${a.upcoming_visits} upcoming` : null, icon: Gauge, chip: "bg-teal-50 text-teal-700" },
        {
          label: "Citizens monitored",
          value: a.citizens ? `${a.citizens_monitored} of ${a.citizens}` : "—",
          sub: a.citizens ? `${Math.round((a.citizens_monitored / a.citizens) * 100)}% sent a reading` : null,
          icon: Users,
          chip: "bg-indigo-50 text-indigo-700",
        },
        { label: "Examinations recorded", value: cur.examinations, sub: delta(cur.examinations, prev.examinations, showDelta), icon: Stethoscope, chip: "bg-violet-50 text-violet-700" },
        { label: "Advisories given", value: cur.advisories, sub: delta(cur.advisories, prev.advisories, showDelta), icon: Megaphone, chip: "bg-orange-50 text-orange-700" },
        {
          label: "Open flags",
          value: a.flags_open,
          sub: a.flags_critical ? `${a.flags_critical} critical` : null,
          tone: a.flags_critical ? "text-red-700" : a.flags_open ? "text-amber-700" : undefined,
          icon: Flag,
          chip: a.flags_critical ? "bg-red-50 text-red-700" : "bg-rose-50 text-rose-700",
        },
      ]
    : [];
  const weeks = (a?.weeks ?? []).map((w) => ({ label: weekLabel(w.start), done: w.done || null, missed: w.missed || null, scheduled: w.scheduled }));
  const anyVisits = weeks.some((w) => w.done || w.missed);
  const selectCls = "min-h-9 rounded-lg border border-line bg-surface px-3 text-[13px] text-ink focus-visible:outline-2 focus-visible:outline-ink";

  return (
    <section className={cx(CARD, "p-5 md:p-6")} aria-labelledby="centre-activity-title">
      <header className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="centre-activity-title" className="text-xl text-ink">PHC worker activity</h2>
          {a && <p className="text-[13px] text-ink-muted">{a.name} · {a.workers} {a.workers === 1 ? "worker" : "workers"}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {searchable && (
            <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Find a centre" aria-label="Find a centre" className={cx(selectCls, "w-40")} />
          )}
          <select aria-label="Health centre" value={centre} onChange={(e) => setCentre(e.target.value)} className={selectCls}>
            {shown.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
          <select aria-label="Period" value={days} onChange={(e) => setDays(Number(e.target.value))} className={selectCls}>
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
        </div>
      </header>
      {!a ? (
        <Loading />
      ) : (
        <>
          <ul className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {tiles.map((tile) => (
              <li key={tile.label} className="flex min-h-[104px] flex-col rounded-xl border border-line bg-surface p-4 transition-colors hover:border-ink/25">
                <span className="flex items-start justify-between gap-2">
                  <span className={LABEL}>{tile.label}</span>
                  <span className={cx("grid h-8 w-8 shrink-0 place-items-center rounded-lg", tile.chip)}>
                    <tile.icon size={16} strokeWidth={1.75} aria-hidden="true" />
                  </span>
                </span>
                <span className={cx("mt-1 text-[28px] font-semibold leading-tight tabular-nums", tile.tone ?? "text-ink")}>{tile.value}</span>
                {tile.sub && <span className="mt-auto text-xs text-ink-muted">{tile.sub}</span>}
              </li>
            ))}
          </ul>
          <div className="mt-6">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-sm font-medium text-ink">Visits per week</p>
              <p className="flex items-center gap-3 text-xs text-ink-muted">
                <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-[#4a7bb0]" />Done</span>
                <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-amber-400" />Missed</span>
              </p>
            </div>
            <div
              className="h-48 md:h-56"
              role="img"
              aria-label={`Visits ${weekLabel(a.range_start)} to ${weekLabel(a.range_end)}: ${cur!.done} done, ${cur!.missed} missed of ${cur!.scheduled} scheduled.`}
            >
              {anyVisits ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={weeks} margin={{ top: 8, right: 4, bottom: 0, left: -20 }}>
                    <CartesianGrid vertical={false} stroke="currentColor" strokeOpacity={0.1} />
                    <XAxis dataKey="label" tickLine={false} axisLine={false} fontSize={12} />
                    <YAxis allowDecimals={false} tickLine={false} axisLine={false} fontSize={12} />
                    <Tooltip
                      cursor={{ fillOpacity: 0.05 }}
                      formatter={(v, name) => [v ?? 0, name === "done" ? "Done" : "Missed"]}
                      labelFormatter={(l, p) => `Week of ${l} · ${p?.[0]?.payload?.scheduled ?? 0} scheduled`}
                    />
                    <Bar dataKey="done" stackId="v" fill="#4a7bb0" isAnimationActive={!reduced()} />
                    <Bar dataKey="missed" stackId="v" fill="#fbbf24" radius={[4, 4, 0, 0]} isAnimationActive={!reduced()} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="grid h-full place-items-center rounded-xl border border-dashed border-line text-[13px] text-ink-muted">
                  No visits recorded in this period
                </div>
              )}
            </div>
            <p className="mt-1 text-xs text-ink-muted">{weekLabel(a.range_start)} – {weekLabel(a.range_end)}, in 7-day buckets.</p>
          </div>
        </>
      )}
    </section>
  );
}

export function AdminDashboard() {
  const res = useResource((s) => getOverview(s), "overview");
  const o = res.data;
  const pct = (a: number, b: number) => (b ? Math.round((a / b) * 100) : 0);

  return (
    <>
      <header className="mb-6">
        <h1 className="text-4xl text-ink md:text-5xl">Admin</h1>
        <p className="mt-1 text-lg font-medium text-ink-soft">Dashboard{o?.area ? ` · ${o.area} district` : " · Tamil Nadu"}</p>
      </header>
      {res.error && <ErrorNote message={res.error} onRetry={res.reload} />}
      {!o ? (
        !res.error && <Loading />
      ) : (
        <div className="flex flex-col gap-6">
          <div className="grid gap-4 md:grid-cols-2">
            <ActionCard
              icon={ClipboardList}
              title="Worker applications waiting"
              value={o.pending_applications}
              sub={o.oldest_pending_at ? `Oldest sent ${fmtAgo(o.oldest_pending_at)}` : "Nobody is waiting"}
              tone={o.pending_applications === 0 ? "ok" : o.pending_over_3_days > 0 ? "bad" : "warn"}
              stats={[
                { icon: Clock, label: "Received today", value: o.pending_today },
                { icon: Hourglass, label: "Waiting over 3 days", value: o.pending_over_3_days },
              ]}
              slices={[
                { label: "Today", value: o.pending_today, color: "#60a5fa" },
                { label: "1 to 3 days", value: Math.max(0, o.pending_applications - o.pending_today - o.pending_over_3_days), color: "#fbbf24" },
                { label: "Over 3 days", value: o.pending_over_3_days, color: "#f87171" },
              ]}
              to={paths.adminApplications}
              cta="Review applications"
            />
            <ActionCard
              icon={MessageSquareText}
              title="Support concerns open"
              value={o.open_concerns}
              sub={`${o.concerns_in_review} in review, ${Math.max(0, o.open_concerns - o.concerns_in_review)} not picked up yet`}
              tone={o.open_concerns === 0 ? "ok" : "warn"}
              stats={[
                { icon: Clock, label: "In review", value: o.concerns_in_review },
                { icon: Inbox, label: "Not picked up yet", value: Math.max(0, o.open_concerns - o.concerns_in_review) },
              ]}
              slices={[
                { label: "In review", value: o.concerns_in_review, color: "#60a5fa" },
                { label: "Not picked up", value: Math.max(0, o.open_concerns - o.concerns_in_review), color: "#fbbf24" },
              ]}
              to={paths.adminConcerns}
              cta="Answer concerns"
            />
            <ActionCard
              icon={Building2}
              title="Workers with no health centre"
              value={o.workers_without_facility}
              sub="They cannot see any citizens until linked."
              tone={o.workers_without_facility > 0 ? "bad" : o.centres_without_workers > 0 ? "warn" : "ok"}
              stats={[
                { icon: UserX, label: "Workers without centre", value: o.workers_without_facility },
                { icon: Building2, label: "Centres without a worker", value: `${o.centres_without_workers} of ${o.facilities_active}` },
              ]}
              slices={[
                { label: "Centres with a worker", value: o.facilities_active - o.centres_without_workers, color: "#4ade80" },
                { label: "Centres without one", value: o.centres_without_workers, color: "#f87171" },
              ]}
              to={paths.adminCentres}
              cta="Open health centres"
            />
            <ActionCard
              icon={AlertTriangle}
              title="Open flags across all centres"
              value={o.open_flags}
              sub={`${o.open_flags_high} of them high or critical`}
              tone={o.open_flags_high > 0 ? "bad" : o.open_flags ? "warn" : "ok"}
              stats={[
                { icon: AlertTriangle, label: "High or critical", value: o.open_flags_high },
                { icon: Activity, label: "Medium or low", value: o.open_flags - o.open_flags_high },
              ]}
              slices={[
                { label: "High or critical", value: o.open_flags_high, color: "#f87171" },
                { label: "Medium or low", value: o.open_flags - o.open_flags_high, color: "#d1d5db" },
              ]}
              to={paths.outbreaks}
              cta="See outbreak signals"
            >
              <div className="mt-3">
                <span className="flex h-2 overflow-hidden rounded-full bg-gray-200">
                  <span className="h-full bg-red-400" style={{ width: `${pct(o.open_flags_high, o.open_flags)}%` }} />
                </span>
                <span className="mt-1.5 flex justify-between text-xs text-ink-soft">
                  <span>
                    <span className="mr-1 inline-block h-2 w-2 rounded-full bg-red-400" />
                    {o.open_flags_high} high or critical ({pct(o.open_flags_high, o.open_flags)}%)
                  </span>
                  <span>
                    <span className="mr-1 inline-block h-2 w-2 rounded-full bg-gray-300" />
                    {o.open_flags - o.open_flags_high} medium or low ({pct(o.open_flags - o.open_flags_high, o.open_flags)}%)
                  </span>
                </span>
              </div>
            </ActionCard>
          </div>

          <AccountsCard o={o} />
          <CentreActivityCard />

          <div className="grid gap-6 lg:grid-cols-2">
            <ActivityCard title="Citizen activity" data={o.citizen_activity} color="#22c55e" />
            <ActivityCard title="PHC worker activity" data={o.worker_activity} color="#eab308" />
          </div>

          <ResearchExport />
        </div>
      )}
    </>
  );
}
