import { useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { Bar, CartesianGrid, ComposedChart, Label, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ArrowDown, ArrowUp, ChevronRight, ClipboardCheck, FileHeart, Minus, Users, UserRoundSearch } from "lucide-react";
import { AXIS, CLEAR_GREEN, Chips, FLAG_RED, Legend, Share, StatTile, TipBox, TipRow } from "../../components/app/charts";
import { BookVisitForm, PersonLine, ResolveControls, workerState } from "../../components/app/phc";
import { Detail, Modal } from "../../components/app/visits";
import { Btn, Card, Empty, Loading, PageHeader, SeverityBadge, VisitBadge, cx } from "../../components/app/ui";
import { useAuth } from "../../context/AuthContext";
import { fmtAgo, fmtDate, fmtDateTime, fmtShortDay, fmtVisit, plural } from "../../lib/format";
import { citizenRecordPath, paths } from "../../lib/routes";
import { SEVERITIES, SEVERITY, type Severity } from "../../lib/severity";
import { useResource } from "../../lib/useResource";
import { getDashboard, getOverview, getWorklist, resolveCitizen, type Kpi, type WorkItem } from "../../services/phc";

const ROWS = 8;
const RANK: Record<Severity, number> = { critical: 0, high: 1, moderate: 2, low: 3 };
const SEV_COLOR: Record<Severity, string> = {
  critical: "rgb(var(--hn-sev-critical))",
  high: "rgb(var(--hn-sev-high))",
  moderate: "rgb(var(--hn-sev-moderate))",
  low: "rgb(var(--hn-sev-low))",
};

type View = "urgent" | "latest" | "all";

function greeting() {
  const hour = Number(new Intl.DateTimeFormat("en-IN", { hour: "numeric", hourCycle: "h23", timeZone: "Asia/Kolkata" }).format(new Date()));
  return hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
}

export function PhcDashboard() {
  const { user } = useAuth();
  const dash = useResource((s) => getDashboard(s), "dashboard");
  const overview = useResource((s) => getOverview(s), "overview");
  const work = useResource((s) => getWorklist({}, s), "worklist");

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
      <PageHeader
        title={`${greeting()}, ${user?.name.split(" ")[0] ?? "there"}`}
        lead={`${d.facility.name} · ${d.facility.district}${d.facility.block ? ` · ${d.facility.block}` : ""}`}
      />

      <div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile icon={UserRoundSearch} tone={d.citizens_flagged ? "danger" : "success"} label="People needing review" value={d.citizens_flagged} hint={plural(d.open_flags, "open flag")} />
        <StatTile
          icon={ClipboardCheck}
          tone={d.visits_needing_outcome ? "warn" : "success"}
          label="Visits needing an outcome"
          value={d.visits_needing_outcome}
          hint={`${plural(d.visits_today, "visit")} later today`}
        />
        <StatTile icon={Users} tone="info" label="Citizens in your area" value={d.citizens} hint={`${d.engagement.ok} submitting regularly`} />
        <StatTile icon={FileHeart} label="Readings, last 7 days" value={d.readings_last_7_days} hint={`from ${plural(d.citizens_submitting_last_7_days, "citizen")}`} />
      </div>

      <div className="mb-6 grid gap-6 lg:grid-cols-2">
        <Card title="Open flags by severity" aside={<span className="text-xs text-ink-soft">{plural(d.open_flags, "flag")}</span>}>
          <Share label="Open flags by severity" parts={SEVERITIES.map((s) => ({ value: d.open_by_severity[s] ?? 0, color: SEV_COLOR[s], label: SEVERITY[s].label }))} />
        </Card>
        <Card title="How citizens are engaging" aside={<span className="text-xs text-ink-soft">{plural(d.citizens, "citizen")}</span>}>
          <Share
            label="Citizen engagement"
            parts={[
              { value: d.engagement.ok, color: CLEAR_GREEN, label: "Submitting" },
              { value: d.engagement.attention, color: FLAG_RED, label: "Has open flags" },
              { value: d.engagement.silent, color: "#ca8a04", label: `Silent ${d.silent_after_days}+ days` },
              { value: d.engagement.never_logged, color: "rgb(var(--hn-line-strong, 160 160 160))", label: "Never submitted" },
            ]}
          />
        </Card>
      </div>

      <NeedsReview items={work.data?.items ?? null} error={work.error} loading={work.loading} onChanged={refresh} />

      <Card title="Last 8 weeks">
        {overview.data ? <Weekly kpis={overview.data.kpis} /> : overview.error ? <p className="text-sm text-danger">{overview.error}</p> : <Loading />}
      </Card>
    </>
  );
}

function NeedsReview({ items, error, loading, onChanged }: { items: WorkItem[] | null; error: string | null; loading: boolean; onChanged: () => void }) {
  const [view, setView] = useState<View>("urgent");
  const [openId, setOpenId] = useState<string | null>(null);

  const rows = useMemo(() => {
    const all = items ?? [];
    if (view === "urgent") return all.filter((i) => i.worst_severity === "critical" || i.worst_severity === "high").sort((a, b) => RANK[a.worst_severity] - RANK[b.worst_severity] || b.last_flagged_at.localeCompare(a.last_flagged_at));
    if (view === "latest") return [...all].sort((a, b) => b.last_flagged_at.localeCompare(a.last_flagged_at));
    return [...all].sort((a, b) => RANK[a.worst_severity] - RANK[b.worst_severity]);
  }, [items, view]);
  const urgent = (items ?? []).filter((i) => i.worst_severity === "critical" || i.worst_severity === "high").length;
  const shown = rows.slice(0, ROWS);
  const opened = items?.find((i) => i.citizen.id === openId) ?? null;

  return (
    <Card
      className="mb-6"
      title="Needs review"
      aside={
        <Link to={paths.phcAlerts} className="inline-flex items-center gap-1 text-sm font-semibold text-blue-700 hover:underline">
          Full worklist <ChevronRight size={15} aria-hidden="true" />
        </Link>
      }
    >
      <div className="mb-4">
        <Chips
          label="Show"
          value={view}
          onChange={setView}
          options={[
            { id: "urgent", label: `Critical and high (${urgent})` },
            { id: "latest", label: "Most recent" },
            { id: "all", label: `All (${items?.length ?? 0})` },
          ]}
        />
      </div>
      {error ? (
        <p className="text-sm text-danger">{error}</p>
      ) : !items ? (
        <Loading />
      ) : shown.length === 0 ? (
        <Empty title={view === "urgent" ? "Nobody at critical or high severity" : "Nobody needs review"} />
      ) : (
        <div className={cx("-mx-5 overflow-x-auto md:-mx-6", loading && "opacity-60")}>
          <table className="w-full min-w-[680px] text-left text-sm">
            <thead className="border-y border-line text-xs font-semibold uppercase tracking-[0.06em] text-ink-soft">
              <tr>
                <th className="px-5 py-3 font-semibold md:px-6">Status</th>
                <th className="px-3 py-3 text-center font-semibold">Flags</th>
                <th className="px-3 py-3 font-semibold">Name</th>
                <th className="px-3 py-3 font-semibold">Details</th>
                <th className="px-3 py-3 font-semibold">Last flagged</th>
                <th className="w-10 px-3 py-3"><span className="visually-hidden">Open</span></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {shown.map((i) => (
                <tr
                  key={i.citizen.id}
                  tabIndex={0}
                  onClick={() => setOpenId(i.citizen.id)}
                  onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), setOpenId(i.citizen.id))}
                  className="cursor-pointer hover:bg-paper focus-visible:bg-paper focus-visible:outline-none"
                >
                  <td className="px-5 py-3.5 md:px-6"><SeverityBadge severity={i.worst_severity} /></td>
                  <td className="px-3 py-3.5 text-center font-semibold tabular-nums text-ink">{i.open_flags}</td>
                  <td className="px-3 py-3.5">
                    <p className="font-semibold text-ink">{i.citizen.name}</p>
                    <p className="text-xs text-ink-soft">{i.citizen.area ?? i.citizen.ref}</p>
                  </td>
                  <td className="max-w-72 px-3 py-3.5 text-ink">
                    <p className="truncate">{i.worst_signal ?? "Reading outside the usual range"}</p>
                    {i.next_visit && <p className="text-xs text-ink-soft">Visit {fmtVisit(i.next_visit.scheduled_for)}</p>}
                  </td>
                  <td className="whitespace-nowrap px-3 py-3.5 text-ink-soft">{fmtAgo(i.last_flagged_at)}</td>
                  <td className="px-3 py-3.5 text-ink-muted"><ChevronRight size={16} aria-hidden="true" /></td>
                </tr>
              ))}
            </tbody>
          </table>
          {rows.length > shown.length && (
            <p className="mt-3 px-5 text-xs text-ink-soft md:px-6">
              Showing {shown.length} of {rows.length}.{" "}
              <Link to={paths.phcAlerts} className="font-semibold text-blue-700 underline">See everyone</Link>
            </p>
          )}
        </div>
      )}
      {opened && (
        <WorkDetails
          item={opened}
          onClose={() => setOpenId(null)}
          onChanged={() => {
            setOpenId(null);
            onChanged();
          }}
        />
      )}
    </Card>
  );
}

function WorkDetails({ item, onClose, onChanged }: { item: WorkItem; onClose: () => void; onChanged: () => void }) {
  const [booking, setBooking] = useState(false);
  return (
    <Modal title={item.citizen.name} onClose={onClose} wide>
      <div className="flex flex-col gap-5">
        <div className="flex flex-wrap items-center gap-5">
          <SeverityBadge severity={item.worst_severity} />
          <span className="text-sm text-ink-soft">{plural(item.open_flags, "open flag")}</span>
        </div>
        <PersonLine person={item.citizen} />
        <dl className="grid gap-4 sm:grid-cols-2">
          <Detail label="Main concern">{item.worst_signal ?? "Reading outside the usual range"}</Detail>
          <Detail label="Last flagged">{fmtDateTime(item.last_flagged_at)}</Detail>
          {item.open_flags > 1 && <Detail label="First flagged">{fmtDateTime(item.first_flagged_at)}</Detail>}
          <Detail label="Next visit">
            {item.next_visit ? (
              <span className="inline-flex flex-wrap items-center gap-2">
                {fmtVisit(item.next_visit.scheduled_for)} <VisitBadge state={item.next_visit.state} />
              </span>
            ) : (
              "None booked"
            )}
          </Detail>
        </dl>
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.06em] text-ink-soft">Flags</p>
          <table className="w-full text-left text-sm">
            <tbody className="divide-y divide-line">
              {item.flags.map((f) => (
                <tr key={f.processed_id}>
                  <td className="py-2 pr-3"><SeverityBadge severity={f.severity} /></td>
                  <td className="py-2 pr-3 text-ink">{f.signal ?? "Outside the usual range"}</td>
                  <td className="whitespace-nowrap py-2 text-right text-xs text-ink-soft">{fmtDateTime(f.measured_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {item.open_flags > item.flags_shown && <p className="mt-1 text-xs text-ink-soft">Showing the worst {item.flags_shown} of {item.open_flags}.</p>}
        </div>
        <div className="flex flex-wrap items-start gap-2 border-t border-line pt-4">
          <ResolveControls
            reviewLabel={item.open_flags > 1 ? `Resolve all ${item.open_flags}` : "Mark seen"}
            onResolve={async (body) => {
              await resolveCitizen(item.citizen.id, body);
              onChanged();
            }}
          />
          {!item.next_visit && <Btn tone="info" onClick={() => setBooking((b) => !b)}>Book visit</Btn>}
          <Link to={citizenRecordPath(item.citizen.id)} className="inline-flex min-h-11 items-center rounded-full px-4 text-sm font-semibold text-ink underline-offset-4 hover:underline">
            Open record
          </Link>
        </div>
        {booking && <BookVisitForm citizen={item.citizen} caseId={item.flags[0]?.processed_id} onCancel={() => setBooking(false)} onBooked={onChanged} />}
      </div>
    </Modal>
  );
}

const UNIT: Record<string, string> = { readings: "Readings", active_citizens: "Citizens", flags_raised: "Flags", flags_cleared: "Flags" };
function Weekly({ kpis }: { kpis: Kpi[] }) {
  const [view, setView] = useState<string>(kpis[0]?.key ?? "readings");
  const raised = kpis.find((k) => k.key === "flags_raised");
  const cleared = kpis.find((k) => k.key === "flags_cleared");
  const compare = view === "compare" && raised && cleared;
  const kpi = kpis.find((k) => k.key === view) ?? kpis[0];
  if (!kpi) return <Empty title="No data yet" />;

  const options = [
    ...kpis.map((k) => ({ id: k.key, label: k.label })),
    ...(raised && cleared ? [{ id: "compare", label: "Raised vs cleared" }] : []),
  ];

  const data = (compare ? raised : kpi).weeks.map((w, i) => ({
    week: w.week_start,
    partial: w.partial,
    value: w.value,
    cleared: compare ? cleared.weeks[i]?.value ?? 0 : undefined,
  }));
  const full = data.filter((w) => !w.partial);
  const avg = full.length ? full.reduce((a, w) => a + w.value, 0) / full.length : 0;
  const last = full[full.length - 1];
  const before = full[full.length - 2];
  const delta = last && before ? last.value - before.value : null;
  const current = data[data.length - 1];
  const yLabel = compare ? "Flags" : UNIT[kpi.key] ?? kpi.label;
  const color = compare || kpi.key === "flags_raised" ? FLAG_RED : kpi.key === "flags_cleared" ? CLEAR_GREEN : AXIS.brand;

  return (
    <>
      <div className="mb-4">
        <Chips label="Measure" value={compare ? "compare" : kpi.key} onChange={setView} options={options} />
      </div>
      <dl className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Fig label="Last full week" value={last?.value ?? 0} />
        <Fig
          label="Change from the week before"
          value={
            delta === null ? "—" : (
              <span className="inline-flex items-center gap-1">
                {delta > 0 ? <ArrowUp size={18} aria-hidden="true" /> : delta < 0 ? <ArrowDown size={18} aria-hidden="true" /> : <Minus size={18} aria-hidden="true" />}
                {Math.abs(delta)}
              </span>
            )
          }
        />
        <Fig label="Weekly average" value={avg.toFixed(avg < 10 ? 1 : 0)} />
        <Fig label="This week so far" value={current?.partial ? current.value : "—"} />
      </dl>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 16, right: 16, bottom: 24, left: 8 }} barGap={4}>
            <CartesianGrid stroke={AXIS.line} strokeDasharray="3 4" vertical={false} />
            <XAxis dataKey="week" tickFormatter={fmtShortDay} tick={AXIS.tick} tickLine={false} axisLine={{ stroke: AXIS.line }}>
              <Label value="Week starting (Monday)" position="insideBottom" offset={-14} style={AXIS.label} />
            </XAxis>
            <YAxis allowDecimals={false} tick={AXIS.tick} axisLine={false} tickLine={false} width={48}>
              <Label value={yLabel} angle={-90} position="insideLeft" style={{ ...AXIS.label, textAnchor: "middle" }} />
            </YAxis>
            {!compare && avg > 0 && (
              <ReferenceLine y={avg} stroke={AXIS.ink} strokeDasharray="5 4">
                <Label value={`Average ${avg.toFixed(avg < 10 ? 1 : 0)}`} position="insideTopRight" style={{ ...AXIS.label, fontWeight: 500 }} />
              </ReferenceLine>
            )}
            <Tooltip
              cursor={{ fill: "rgb(var(--hn-ink) / 0.05)" }}
              content={({ active, payload }) => {
                const w = active && (payload?.[0]?.payload as (typeof data)[number] | undefined);
                if (!w) return null;
                const i = data.indexOf(w);
                const prev = i > 0 ? data[i - 1] : null;
                return (
                  <TipBox title={`Week of ${fmtDate(w.week)}${w.partial ? " (so far)" : ""}`}>
                    {compare ? (
                      <>
                        <TipRow color={FLAG_RED} label="Flags raised" value={w.value} />
                        <TipRow color={CLEAR_GREEN} label="Flags cleared" value={w.cleared ?? 0} />
                        <TipRow label="Net change" value={`${w.value - (w.cleared ?? 0) > 0 ? "+" : ""}${w.value - (w.cleared ?? 0)}`} />
                      </>
                    ) : (
                      <>
                        <TipRow color={color} label={kpi.label} value={w.value} />
                        {prev && <TipRow label="Week before" value={`${prev.value} (${w.value - prev.value >= 0 ? "+" : ""}${w.value - prev.value})`} />}
                      </>
                    )}
                  </TipBox>
                );
              }}
            />
            <Bar dataKey="value" name={compare ? "Flags raised" : kpi.label} radius={[4, 4, 0, 0]} maxBarSize={44} isAnimationActive={false} fill={color} shape={(p: unknown) => <PartialBar {...(p as BarShape)} fill={color} />} />
            {compare && <Bar dataKey="cleared" name="Flags cleared" radius={[4, 4, 0, 0]} maxBarSize={44} isAnimationActive={false} fill={CLEAR_GREEN} shape={(p: unknown) => <PartialBar {...(p as BarShape)} fill={CLEAR_GREEN} />} />}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <Legend
        items={[
          ...(compare
            ? [
                { color: FLAG_RED, label: "Flags raised" },
                { color: CLEAR_GREEN, label: "Flags cleared" },
              ]
            : [{ color, label: kpi.label }]),
          { color, label: "This week, so far", faded: true },
          ...(!compare ? [{ color: AXIS.ink, label: "8-week average", dashed: true }] : []),
        ]}
      />
      <p className="sr-only">
        Weekly values, oldest first: {data.map((w) => `${fmtShortDay(w.week)} ${w.value}${w.partial ? " so far" : ""}`).join(", ")}
      </p>
    </>
  );
}

interface BarShape {
  x: number;
  y: number;
  width: number;
  height: number;
  fill: string;
  payload: { partial: boolean };
}

function PartialBar({ x, y, width, height, fill, payload }: BarShape) {
  if (!height || height < 0) return null;
  const r = Math.min(4, width / 2, height);
  return (
    <path
      d={`M${x},${y + height}V${y + r}Q${x},${y} ${x + r},${y}H${x + width - r}Q${x + width},${y} ${x + width},${y + r}V${y + height}Z`}
      fill={fill}
      fillOpacity={payload.partial ? 0.35 : 1}
      stroke={payload.partial ? fill : "none"}
      strokeDasharray={payload.partial ? "3 3" : undefined}
    />
  );
}

function Fig({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-2xl bg-paper-raised px-4 py-3">
      <dt className="text-xs text-ink-soft">{label}</dt>
      <dd className="mt-0.5 font-display text-2xl tabular-nums text-ink">{value}</dd>
    </div>
  );
}

