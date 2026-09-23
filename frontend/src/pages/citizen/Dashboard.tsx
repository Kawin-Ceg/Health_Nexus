import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowDown, ArrowUp, CalendarClock, Minus, PlusCircle, ShieldAlert } from "lucide-react";
import { Card, Empty, ErrorNote, Loading, PageHeader, Stat, VisitBadge, cx } from "../../components/app/ui";
import { TrendChart } from "../../components/app/TrendChart";
import { useAuth } from "../../context/AuthContext";
import { fmtAgo, fmtDateTime, fmtVisit, plural } from "../../lib/format";
import { paths } from "../../lib/routes";
import { useResource } from "../../lib/useResource";
import { getMetrics, getSummary, type Metric } from "../../services/health";

const POSITION = {
  below: { label: "Below normal", icon: ArrowDown, cls: "text-warn" },
  above: { label: "Above normal", icon: ArrowUp, cls: "text-warn" },
  normal: { label: "In normal range", icon: Minus, cls: "text-success" },
} as const;

export function CitizenDashboard() {
  const { user } = useAuth();
  const { data, error, loading, reload } = useResource(
    (signal) => Promise.all([getSummary(signal), getMetrics()]),
    "summary",
  );
  const [chosen, setChosen] = useState<string | null>(null);

  const [summary, info] = data ?? [null, null];
  const metrics = useMemo(() => new Map((info?.metrics ?? []).map((m) => [m.key, m])), [info]);
  const charted = useMemo(
    () => (info?.metrics ?? []).filter((m) => summary?.trend.some((p) => p.vitals[m.key] !== undefined)),
    [info, summary],
  );
  const metric: Metric | undefined = charted.find((m) => m.key === chosen) ?? charted[0];

  if (loading && !data) return <Loading label="Loading your dashboard" />;
  if (error || !summary || !info) return <ErrorNote message={error ?? "Could not load your dashboard."} onRetry={reload} />;

  const unreviewed = !summary.facility || summary.facility.workers_assigned === 0;
  const points = metric
    ? summary.trend
        .filter((p) => p.vitals[metric.key] !== undefined)
        .map((p) => ({ measured_at: p.measured_at, value: p.vitals[metric.key], flagged: p.flagged }))
    : [];

  return (
    <>
      <PageHeader
        title={`Hello, ${user?.name.split(" ")[0] ?? "there"}`}
        lead={summary.facility ? `Your health centre: ${summary.facility.name}` : undefined}
        actions={
          <Link
            to={paths.submitVitals}
            className="inline-flex min-h-10 items-center gap-2 rounded-xl bg-brand px-4 text-sm font-semibold text-on-brand hover:opacity-90"
          >
            <PlusCircle size={18} aria-hidden="true" /> Log vitals
          </Link>
        }
      />

      {unreviewed && (
        <div role="alert" className="mb-6 flex gap-3 rounded-2xl border border-danger/30 bg-danger-soft p-4 text-sm text-danger">
          <ShieldAlert size={20} aria-hidden="true" className="shrink-0" />
          <p>
            <strong>Nobody is reviewing your readings.</strong>{" "}
            {summary.facility
              ? "No health worker is assigned to your centre yet."
              : "Your account is not linked to a health centre."}{" "}
            <Link to={`${paths.settings}?tab=centre`} className="font-semibold underline">
              Choose a staffed centre
            </Link>
            . If you feel unwell, see a doctor.
          </p>
        </div>
      )}

      <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Readings, last 7 days" value={summary.readings_last_7_days} hint={`${plural(summary.readings_total, "reading")} in total`} />
        <Stat label="Flags awaiting review" value={summary.open_flags} tone={summary.open_flags ? "warn" : undefined} />
        <Stat label="Unread alerts" value={summary.unread_alerts} />
        <Stat
          label="Next visit"
          value={summary.next_visit ? <span className="text-base">{fmtVisit(summary.next_visit.scheduled_for)}</span> : "None"}
          hint={summary.next_visit ? <VisitBadge state={summary.next_visit.state} /> : undefined}
        />
      </div>

      <Card
        className="mb-6"
        title="Latest readings"
        aside={
          summary.readings_until_baseline > 0 && (
            <p className="text-xs text-ink-soft">
              Compared with published ranges. Your personal baseline needs{" "}
              {plural(summary.readings_until_baseline, "more reading")} in the last {summary.baseline_window_days} days.
            </p>
          )
        }
      >
        {summary.latest.length === 0 ? (
          <Empty title="No readings yet">
            <Link to={paths.submitVitals} className="font-semibold text-brand underline">
              Log your first reading
            </Link>{" "}
            to start tracking.
          </Empty>
        ) : (
          <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {summary.latest.map((v) => {
              const m = metrics.get(v.key);
              if (!m) return null;
              const pos = POSITION[v.position];
              return (
                <li key={v.key} className="rounded-xl border border-line p-4">
                  <p className="text-sm text-ink-soft">{m.label}</p>
                  <p className="mt-1 text-2xl font-semibold tabular-nums text-ink">
                    {v.value.toFixed(m.decimals)} <span className="text-sm font-normal text-ink-soft">{m.unit}</span>
                  </p>
                  <p className={cx("mt-1 flex items-center gap-1 text-xs font-medium", pos.cls)}>
                    <pos.icon size={12} aria-hidden="true" /> {m.normal ? pos.label : "No normal range"}
                  </p>
                  <p className="mt-2 text-xs text-ink-soft">
                    {v.baseline
                      ? `Your usual: ${v.baseline.mean.toFixed(m.decimals)} ± ${v.baseline.sd.toFixed(m.decimals)} (${v.baseline.n} readings)`
                      : m.normal
                        ? `Normal: ${m.normal[0]}–${m.normal[1]} ${m.unit}`
                        : "Tracked for your record"}
                  </p>
                  <p className="text-xs text-ink-soft">{fmtAgo(v.measured_at)}</p>
                </li>
              );
            })}
          </ul>
        )}
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card
          className="lg:col-span-2"
          title={metric ? `${metric.label}, last ${summary.trend_window_days} days` : "Trend"}
          aside={
            charted.length > 1 && (
              <select
                aria-label="Measurement to chart"
                value={metric?.key}
                onChange={(e) => setChosen(e.target.value)}
                className="min-h-9 rounded-lg border border-line bg-surface px-2 text-sm"
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
          <Card title="Open alerts" aside={<Link to={paths.citizenAlerts} className="text-sm font-semibold text-brand">See all</Link>}>
            {summary.alerts.length === 0 ? (
              <p className="text-sm text-ink-soft">Nothing new.</p>
            ) : (
              <ul className="flex flex-col gap-3">
                {summary.alerts.map((a) => (
                  <li key={a.id} className="text-sm">
                    <p className="text-ink">{a.message}</p>
                    <p className="text-xs text-ink-soft">{fmtDateTime(a.created_at)}</p>
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Card title="Next visit">
            {summary.next_visit ? (
              <div className="flex gap-3 text-sm">
                <CalendarClock size={20} className="shrink-0 text-brand" aria-hidden="true" />
                <div>
                  <p className="font-semibold text-ink">{fmtVisit(summary.next_visit.scheduled_for)}</p>
                  {summary.next_visit.worker_name && <p className="text-ink-soft">with {summary.next_visit.worker_name}</p>}
                  {summary.next_visit.reason && <p className="text-ink-soft">{summary.next_visit.reason}</p>}
                  <div className="mt-2">
                    <VisitBadge state={summary.next_visit.state} />
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-sm text-ink-soft">No visit booked.</p>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}
