import { useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis } from "recharts";
import { BookVisitForm, PersonLine, ResolveControls, workerState } from "../../components/app/phc";
import { Btn, Card, Empty, Loading, PageHeader, SeverityBadge, Stat, Tabs, cx } from "../../components/app/ui";
import { fmtAgo, fmtShortDay } from "../../lib/format";
import { oneOf, useQueryState } from "../../lib/params";
import { paths } from "../../lib/routes";
import { SEVERITIES, SEVERITY, type Severity } from "../../lib/severity";
import { useResource } from "../../lib/useResource";
import { getDashboard, getOverview, getQueue, markSeen, type Kpi } from "../../services/phc";

const QUEUE_LIMIT = 25;

function KpiCard({ kpi }: { kpi: Kpi }) {
  const complete = kpi.weeks.filter((w) => !w.partial);
  const last = complete[complete.length - 1];
  const current = kpi.weeks[kpi.weeks.length - 1];
  return (
    <Card>
      <p className="text-xs font-medium uppercase tracking-wide text-ink-soft">{kpi.label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-ink">{last?.value ?? 0}</p>
      <p className="text-xs text-ink-soft">
        last full week · {current.value} so far this week
      </p>
      <div className="mt-3 h-16" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={kpi.weeks} margin={{ top: 0, right: 0, bottom: 0, left: 0 }} barCategoryGap={2}>
            <XAxis dataKey="week_start" hide />
            <Tooltip
              cursor={{ fill: "rgb(var(--hn-ink) / 0.05)" }}
              content={({ active, payload }) => {
                const w = active && (payload?.[0]?.payload as Kpi["weeks"][number] | undefined);
                if (!w) return null;
                return (
                  <div className="rounded-lg border border-line bg-surface px-2 py-1 text-xs shadow-[var(--hn-shadow-md)]">
                    Week of {fmtShortDay(w.week_start)}: <strong>{w.value}</strong>
                    {w.partial && " (so far)"}
                  </div>
                );
              }}
            />
            <Bar dataKey="value" radius={[4, 4, 0, 0]} isAnimationActive={false}>
              {kpi.weeks.map((w) => (
                <Cell key={w.week_start} fill="rgb(var(--hn-brand))" fillOpacity={w.partial ? 0.35 : 1} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="sr-only">
        Weekly values, oldest first: {kpi.weeks.map((w) => `${fmtShortDay(w.week_start)} ${w.value}${w.partial ? " so far" : ""}`).join(", ")}
      </p>
    </Card>
  );
}

export function PhcDashboard() {
  const { params, set } = useQueryState();
  const severity = oneOf(params.get("severity"), SEVERITIES, null);
  const dash = useResource((s) => getDashboard(s), "dashboard");
  const overview = useResource((s) => getOverview(s), "overview");
  const queue = useResource((s) => getQueue({ severity, limit: QUEUE_LIMIT }, s), `queue:${severity}`);
  const [booking, setBooking] = useState<string | null>(null);

  const blocked = workerState(dash);
  if (blocked) return blocked;
  if (!dash.data) return <Loading label="Loading your catchment" />;
  const d = dash.data;

  const refresh = () => {
    queue.reload();
    dash.reload();
  };

  return (
    <>
      <PageHeader title={d.facility.name} lead={`${d.facility.district}${d.facility.block ? ` · ${d.facility.block}` : ""} · everyone registered to this centre`} />

      <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Citizens in catchment" value={d.citizens} hint={`${d.engagement.never_logged} never logged · ${d.engagement.silent} silent ${d.silent_after_days}+ days`} />
        <Stat label="Citizens with open flags" value={d.citizens_flagged} tone={d.citizens_flagged ? "danger" : undefined} hint={`${d.open_flags} open flags`} />
        <Stat label="Readings, last 7 days" value={d.readings_last_7_days} hint={`from ${d.citizens_submitting_last_7_days} citizens`} />
        <Stat
          label="Visits needing an outcome"
          value={d.visits_needing_outcome}
          tone={d.visits_needing_outcome ? "warn" : undefined}
          hint={<Link to={paths.phcSchedule} className="text-brand underline">{d.visits_today} more later today</Link>}
        />
      </div>

      <Card
        className="mb-6"
        title="Triage queue"
        aside={<span className="text-xs text-ink-soft">Worst first · {queue.data ? `${queue.data.total} open` : "…"}</span>}
      >
        <Tabs
          label="Severity"
          value={severity ?? "all"}
          onChange={(v) => set({ severity: v === "all" ? null : v })}
          tabs={[
            { id: "all" as const, label: `All (${d.open_flags})` },
            ...SEVERITIES.map((s: Severity) => ({ id: s, label: `${SEVERITY[s].label} (${d.open_by_severity[s]})` })),
          ]}
        />
        {queue.error ? (
          <p className="text-sm text-danger">{queue.error}</p>
        ) : !queue.data ? (
          <Loading />
        ) : queue.data.items.length === 0 ? (
          <Empty title={severity ? `No open ${SEVERITY[severity].label.toLowerCase()} flags` : "No open flags"}>
            Every flagged reading in your catchment has been reviewed.
          </Empty>
        ) : (
          <ul className={cx("divide-y divide-line", queue.loading && "opacity-60")}>
            {queue.data.items.map((c) => (
              <li key={c.processed_id} className="py-4">
                <div className="flex flex-wrap items-start gap-4">
                  <SeverityBadge severity={c.severity} className="mt-0.5" />
                  <div className="min-w-48 flex-1">
                    <PersonLine person={c.citizen} />
                    <p className="mt-1 text-sm text-ink">{c.signal ?? "Reading outside the usual range"}</p>
                    <p className="text-xs text-ink-soft">
                      {fmtAgo(c.measured_at)}
                      {c.symptoms.length > 0 && <span className="capitalize"> · reports {c.symptoms.join(", ")}</span>}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <ResolveControls onResolve={async (body) => { await markSeen(c.processed_id, body); refresh(); }} />
                    <Btn onClick={() => setBooking(booking === c.processed_id ? null : c.processed_id)}>Book visit</Btn>
                  </div>
                </div>
                {booking === c.processed_id && (
                  <BookVisitForm
                    citizen={c.citizen}
                    caseId={c.processed_id}
                    onCancel={() => setBooking(null)}
                    onBooked={() => {
                      setBooking(null);
                      refresh();
                    }}
                  />
                )}
              </li>
            ))}
          </ul>
        )}
        {queue.data && queue.data.total > queue.data.items.length && (
          <p className="mt-3 text-xs text-ink-soft">
            Showing the {queue.data.items.length} worst of {queue.data.total}.{" "}
            <Link to={paths.phcAlerts} className="text-brand underline">See every flagged citizen</Link>
          </p>
        )}
      </Card>

      <h2 className="mb-3 text-base font-semibold text-ink">Last 8 weeks</h2>
      {overview.data ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {overview.data.kpis.map((k) => (
            <KpiCard key={k.key} kpi={k} />
          ))}
        </div>
      ) : overview.error ? (
        <p className="text-sm text-danger">{overview.error}</p>
      ) : (
        <Loading />
      )}
    </>
  );
}
