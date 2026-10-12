import { useMemo } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis } from "recharts";
import { CitizenWorkCard, workerState } from "../../components/app/phc";
import { Card, Empty, LinkBtn, Loading, Stat, Tabs, cx } from "../../components/app/ui";
import { Doodle } from "../../components/landing/Doodle/Doodle";
import { useAuth } from "../../context/AuthContext";
import { Bell, Bot, CalendarDays, Map } from "lucide-react";
import { fmtShortDay, plural } from "../../lib/format";
import { oneOf, useQueryState } from "../../lib/params";
import { paths } from "../../lib/routes";
import { SEVERITIES, SEVERITY, type Severity } from "../../lib/severity";
import { useResource } from "../../lib/useResource";
import { getDashboard, getOverview, getWorklist, type Kpi, type WorkItem } from "../../services/phc";

/** The dashboard shows the worst few; the alerts page has the whole list. */
const PEOPLE_SHOWN = 6;

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
          <BarChart accessibilityLayer={false} data={kpi.weeks} margin={{ top: 0, right: 0, bottom: 0, left: 0 }} barCategoryGap={2}>
            <XAxis dataKey="week_start" hide />
            <Tooltip
              cursor={{ fill: "rgb(var(--hn-ink) / 0.05)" }}
              content={({ active, payload }) => {
                const w = active && (payload?.[0]?.payload as Kpi["weeks"][number] | undefined);
                if (!w) return null;
                return (
                  <div className="rounded-xl border border-line bg-surface px-2 py-1 text-xs shadow-[var(--hn-shadow-md)]">
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

function greeting() {
  const hour = Number(new Intl.DateTimeFormat("en-IN", { hour: "numeric", hourCycle: "h23", timeZone: "Asia/Kolkata" }).format(new Date()));
  return hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
}

export function PhcDashboard() {
  const { user } = useAuth();
  const { params, set } = useQueryState();
  const severity = oneOf(params.get("severity"), SEVERITIES, null);
  const dash = useResource((s) => getDashboard(s), "dashboard");
  const overview = useResource((s) => getOverview(s), "overview");
  const work = useResource((s) => getWorklist({}, s), "worklist");

  const people: WorkItem[] = useMemo(() => work.data?.items ?? [], [work.data]);
  const counts = useMemo(() => {
    const out = { critical: 0, high: 0, moderate: 0, low: 0 } as Record<Severity, number>;
    for (const p of people) out[p.worst_severity] += 1;
    return out;
  }, [people]);
  const filtered = severity ? people.filter((p) => p.worst_severity === severity) : people;
  const shown = filtered.slice(0, PEOPLE_SHOWN);

  const blocked = workerState(dash);
  if (blocked) return blocked;
  if (!dash.data) return <Loading label="Loading your catchment" />;
  const d = dash.data;

  const refresh = () => {
    work.reload();
    dash.reload();
  };

  return (
    <>
      <section className="relative isolate mb-4 overflow-clip rounded-3xl border border-line bg-surface p-6 md:p-8" aria-labelledby="phc-greeting">
        <Doodle piece="radial" className="-right-10 -bottom-16 w-80 [--doodle-opacity:0.6]" />
        <Doodle piece="tree" className="top-4 right-[18%] w-40 [--doodle-opacity:0.5]" />
        <p className="text-xs font-semibold uppercase tracking-[0.06em] text-ink-muted">
          {d.facility.name} · {d.facility.district}
          {d.facility.block ? ` · ${d.facility.block}` : ""}
        </p>
        <h1 id="phc-greeting" className="mt-2 text-3xl text-ink md:text-4xl">
          {greeting()}, {user?.name.split(" ")[0] ?? "there"}
        </h1>
        <p className="mt-2 max-w-xl font-display text-xl leading-snug text-ink-soft md:text-2xl">
          {d.citizens_flagged
            ? `${plural(d.citizens_flagged, "person needs", "people need")} review today.`
            : "Nobody needs review right now."}
          {d.visits_today ? ` ${plural(d.visits_today, "visit")} later today.` : ""}
        </p>
      </section>

      <nav aria-label="Quick actions" className="mb-6 flex flex-wrap gap-2">
        <LinkBtn to={paths.phcAlerts}>
          <Bell size={16} aria-hidden="true" /> Open the worklist
        </LinkBtn>
        <LinkBtn to={paths.phcSchedule}>
          <CalendarDays size={16} aria-hidden="true" /> Today's schedule
        </LinkBtn>
        <LinkBtn to={paths.phcMap}>
          <Map size={16} aria-hidden="true" /> Risk map
        </LinkBtn>
        <LinkBtn to={paths.assistant}>
          <Bot size={16} aria-hidden="true" /> Ask the assistant
        </LinkBtn>
      </nav>

      {/* Ordered by what needs a decision today, not by what is easiest to count. */}
      <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat
          label="People needing review"
          value={d.citizens_flagged}
          tone={d.citizens_flagged ? "danger" : undefined}
          hint={`${plural(d.open_flags, "open flag")} between them`}
        />
        <Stat
          label="Visits needing an outcome"
          value={d.visits_needing_outcome}
          tone={d.visits_needing_outcome ? "warn" : undefined}
          hint={<Link to={paths.phcSchedule} className="text-brand underline">{d.visits_today} more later today</Link>}
        />
        <Stat label="Citizens in catchment" value={d.citizens} hint={`${d.engagement.never_logged} never logged · ${d.engagement.silent} silent ${d.silent_after_days}+ days`} />
        <Stat label="Readings, last 7 days" value={d.readings_last_7_days} hint={`from ${d.citizens_submitting_last_7_days} citizens`} />
      </div>

      {/* Grouped by person: five readings from one citizen are one decision, not
          five. Same card as the alerts page, so the unit of work never changes. */}
      <Card
        className="mb-6"
        title="Needs review today"
        aside={<span className="text-xs text-ink-soft">Worst first{work.data ? ` · ${plural(work.data.total_citizens, "person")}` : ""}</span>}
      >
        <Tabs
          label="Severity"
          value={severity ?? "all"}
          onChange={(v) => set({ severity: v === "all" ? null : v })}
          tabs={[
            { id: "all" as const, label: `All (${people.length})` },
            ...SEVERITIES.filter((s) => counts[s] > 0).map((s: Severity) => ({ id: s, label: `${SEVERITY[s].label} (${counts[s]})` })),
          ]}
        />
        {work.error ? (
          <p className="text-sm text-danger">{work.error}</p>
        ) : !work.data ? (
          <Loading />
        ) : shown.length === 0 ? (
          <Empty title={severity ? `Nobody at ${SEVERITY[severity].label.toLowerCase()} severity` : "Nobody needs review"}>
            Every flagged reading in your catchment has been handled.
          </Empty>
        ) : (
          <>
            <ul className={cx("flex flex-col gap-3", work.loading && "opacity-60")}>
              {shown.map((item) => (
                <CitizenWorkCard key={item.citizen.id} item={item} onChanged={refresh} />
              ))}
            </ul>
            {filtered.length > shown.length && (
              <p className="mt-3 text-xs text-ink-soft">
                Showing the {shown.length} most urgent of {filtered.length}.{" "}
                <Link to={paths.phcAlerts} className="font-semibold text-brand underline">
                  Open the full list
                </Link>
              </p>
            )}
          </>
        )}
      </Card>

      <h2 className="mb-4 text-2xl text-ink">Last 8 weeks</h2>
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
