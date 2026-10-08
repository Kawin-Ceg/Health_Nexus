import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowDown, ArrowUp, CalendarClock, Minus, PlusCircle, ShieldAlert } from "lucide-react";
import { Card, Empty, ErrorNote, Loading, PageHeader, VisitBadge, cx } from "../../components/app/ui";
import { BaselineProgress } from "../../components/app/ModelInsights";
import { TrendChart } from "../../components/app/TrendChart";
import { useAuth } from "../../context/AuthContext";
import { fmtAgo, fmtDateTime, fmtVisit, plural } from "../../lib/format";
import { paths } from "../../lib/routes";
import { useResource } from "../../lib/useResource";
import { getBaselineStatus, getMetrics, getSummary, type Metric } from "../../services/health";

const POSITION = {
  below: { label: "Below normal", icon: ArrowDown, cls: "text-warn" },
  above: { label: "Above normal", icon: ArrowUp, cls: "text-warn" },
  normal: { label: "In normal range", icon: Minus, cls: "text-success" },
} as const;

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

export function CitizenDashboard() {
  const { user } = useAuth();
  const { data, error, loading, reload } = useResource(
    (signal) => Promise.all([getSummary(signal), getMetrics(), getBaselineStatus(signal)]),
    "summary",
  );
  const [chosen, setChosen] = useState<string | null>(null);

  const [summary, info, baselines] = data ?? [null, null, null];
  const metrics = useMemo(() => new Map((info?.metrics ?? []).map((m) => [m.key, m])), [info]);
  const charted = useMemo(
    () => (info?.metrics ?? []).filter((m) => summary?.trend.some((p) => p.vitals[m.key] !== undefined)),
    [info, summary],
  );
  const metric: Metric | undefined = charted.find((m) => m.key === chosen) ?? charted[0];

  if (loading && !data) return <Loading label="Loading your dashboard" />;
  if (error || !summary || !info) return <ErrorNote message={error ?? "Could not load your dashboard."} onRetry={reload} />;

  const unreviewed = !summary.facility || summary.facility.workers_assigned === 0;
  const offNormal = summary.latest.filter((v) => v.position !== "normal");
  const inRange = summary.latest.filter((v) => v.position === "normal");
  const alerts = groupAlerts(summary.alerts.map((a) => a.message));
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
            className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-brand px-4 text-sm font-semibold text-on-brand hover:opacity-90"
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

      {/* One plain-language answer to "am I OK, and is anyone looking at this?".
          Raw counts like "36 flags" and "110 unread alerts" alarm without telling
          anyone what to do, so they moved into the sentence below and the alerts page. */}
      <section className="mb-6 rounded-2xl border border-line bg-surface p-5" aria-labelledby="standing">
        <h2 id="standing" className="sr-only">
          Where you stand
        </h2>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-64 flex-1">
            <p className={cx("flex items-center gap-2 text-lg font-semibold", offNormal.length ? "text-warn" : "text-success")}>
              {offNormal.length ? <ArrowUp size={18} aria-hidden="true" /> : <Minus size={18} aria-hidden="true" />}
              {offNormal.length
                ? `${plural(offNormal.length, "recent reading")} outside your usual range`
                : "Your latest readings are all in your usual range"}
            </p>
            <p className="mt-1 text-sm text-ink-soft">
              {offNormal.length > 0
                ? offNormal.map((v) => metrics.get(v.key)?.label ?? v.key).join(", ")
                : `${plural(summary.readings_last_7_days, "reading")} logged in the last 7 days.`}
              {summary.open_flags > 0 && summary.facility
                ? ` · ${summary.facility.name} has been sent ${plural(summary.open_flags, "flagged reading")} and may contact you.`
                : ""}
            </p>
          </div>
          {summary.next_visit && (
            <div className="rounded-xl bg-paper-raised px-4 py-3 text-sm">
              <p className="flex items-center gap-2 font-semibold text-ink">
                <CalendarClock size={16} className="text-brand" aria-hidden="true" />
                {fmtVisit(summary.next_visit.scheduled_for)}
              </p>
              <p className="text-ink-soft">
                {summary.next_visit.worker_name ? `with ${summary.next_visit.worker_name}` : "Home visit"}
              </p>
            </div>
          )}
        </div>
      </section>

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
          /* Out of range first and drawn larger: the eye should land on the
             reading that needs attention, not read eight identical tiles. */
          <>
            {offNormal.length > 0 && (
              <ul className="mb-4 grid gap-3 sm:grid-cols-2">
                {offNormal.map((v) => {
                  const m = metrics.get(v.key);
                  if (!m) return null;
                  const pos = POSITION[v.position];
                  return (
                    <li key={v.key} className="rounded-xl border border-warn/40 bg-warn/5 p-4">
                      <p className="text-sm font-medium text-ink">{m.label}</p>
                      <p className="mt-1 text-3xl font-semibold tabular-nums text-ink">
                        {v.value.toFixed(m.decimals)} <span className="text-base font-normal text-ink-soft">{m.unit}</span>
                      </p>
                      <p className={cx("mt-1 flex items-center gap-1 text-sm font-semibold", pos.cls)}>
                        <pos.icon size={14} aria-hidden="true" /> {pos.label}
                      </p>
                      <p className="mt-2 text-xs text-ink-soft">
                        {v.baseline
                          ? `Your usual is ${v.baseline.usual.toFixed(m.decimals)} ${m.unit} · ${fmtAgo(v.measured_at)}`
                          : m.normal
                            ? `Normal is ${m.normal[0]}–${m.normal[1]} ${m.unit} · ${fmtAgo(v.measured_at)}`
                            : fmtAgo(v.measured_at)}
                      </p>
                    </li>
                  );
                })}
              </ul>
            )}
            {inRange.length > 0 && (
              <>
                {offNormal.length > 0 && <h3 className="mb-2 text-sm font-medium text-ink-soft">In your usual range</h3>}
                <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
                  {inRange.map((v) => {
                    const m = metrics.get(v.key);
                    if (!m) return null;
                    return (
                      <li key={v.key} className="rounded-xl border border-line px-3 py-2">
                        <p className="text-xs text-ink-soft">{m.label}</p>
                        <p className="text-lg font-semibold tabular-nums text-ink">
                          {v.value.toFixed(m.decimals)} <span className="text-xs font-normal text-ink-soft">{m.unit}</span>
                        </p>
                        <p className="text-xs text-ink-soft">{m.normal ? POSITION[v.position].label : "No normal range"}</p>
                      </li>
                    );
                  })}
                </ul>
              </>
            )}
          </>
        )}
      </Card>

      <div className="grid items-start gap-6 lg:grid-cols-3">
        <Card
          className="lg:col-span-2"
          title={metric ? `${metric.label}, last ${summary.trend_window_days} days` : "Trend"}
          aside={
            charted.length > 1 && (
              <select
                aria-label="Measurement to chart"
                value={metric?.key}
                onChange={(e) => setChosen(e.target.value)}
                className="min-h-11 rounded-lg border border-line bg-surface px-2 text-sm"
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
              <>
                <ul className="flex flex-col gap-3">
                  {summary.alerts.map((a, i) => (
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

      {baselines && baselines.vitals.length > 0 && (
        <Card className="mt-6" title="How well we know your normal">
          <p className="mb-4 max-w-3xl text-sm text-ink-soft">
            Each measurement starts out compared with published normal ranges. From {baselines.min_readings} readings on,
            your own usual values start to count, and from {baselines.full_readings} readings your readings are judged
            against you alone. A fever or very high blood pressure is always flagged, whatever your usual is.
          </p>
          <BaselineProgress status={baselines} metrics={metrics} />
        </Card>
      )}
    </>
  );
}
