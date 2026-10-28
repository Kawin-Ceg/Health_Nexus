import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, ComposedChart, Label, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Activity, FileHeart, ShieldAlert, Users } from "lucide-react";
import { AXIS, Chips, FLAG_RED, Legend, StatTile, TipBox, TipRow } from "../../components/app/charts";
import { workerState } from "../../components/app/phc";
import { Card, Empty, Loading, PageHeader, cx } from "../../components/app/ui";
import { fmtDate, fmtShortDay, plural } from "../../lib/format";
import { oneOf, useQueryState } from "../../lib/params";
import { useResource } from "../../lib/useResource";
import { getReports, type Reports as ReportsData } from "../../services/phc";

const WINDOWS = ["7", "30", "90", "180"] as const;
const WINDOW_LABEL: Record<(typeof WINDOWS)[number], string> = { "7": "7 days", "30": "30 days", "90": "3 months", "180": "6 months" };
const NORMAL = "rgb(var(--hn-forest))";

type Locality = ReportsData["localities"][number];
const SORTS = [
  { id: "readings", label: "Most readings", by: (l: Locality) => l.readings },
  { id: "flags", label: "Most flagged", by: (l: Locality) => l.flags },
  { id: "rate", label: "Highest flag rate", by: (l: Locality) => (l.readings ? l.flags / l.readings : 0) },
  { id: "quiet", label: "Lowest participation", by: (l: Locality) => -(l.citizens ? l.submitting / l.citizens : 0) },
] as const;
type Sort = (typeof SORTS)[number]["id"];

const pct = (n: number, d: number) => (d ? `${Math.round((n / d) * 100)}%` : "—");

export function Reports() {
  const { params, set } = useQueryState();
  const days = oneOf(params.get("days"), WINDOWS, "30");
  const rep = useResource((s) => getReports(Number(days), s), days);
  const blocked = workerState(rep);
  if (blocked) return blocked;
  const r = rep.data;

  return (
    <>
      <PageHeader title="Reports" lead={r ? `${fmtDate(r.window.start)} to ${fmtDate(r.window.end)}` : undefined} />
      <div className="mb-5">
        <Chips
          label="Period"
          value={days}
          onChange={(v) => set({ days: v === "30" ? null : v })}
          options={WINDOWS.map((w) => ({ id: w, label: `Last ${WINDOW_LABEL[w]}` }))}
        />
      </div>
      {!r ? (
        <Loading />
      ) : (
        <div className={cx("flex flex-col gap-6", rep.loading && "opacity-60")}>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <StatTile icon={FileHeart} label="Readings" value={r.readings} hint={`about ${(r.readings / r.window.days).toFixed(1)} a day`} />
            <StatTile icon={Activity} tone="info" label="Citizens who submitted" value={r.citizens_submitting} hint={`${pct(r.citizens_submitting, r.catchment_now)} of your area`} />
            <StatTile
              icon={ShieldAlert}
              tone={r.flags ? "danger" : "success"}
              label="Flagged readings"
              value={r.flags}
              hint={r.flag_rate === null ? "No readings" : `${(r.flag_rate * 100).toFixed(1)}% of readings`}
            />
            <StatTile icon={Users} label="Citizens in your area" value={r.catchment_now} hint="As of today" />
          </div>
          <ReadingsChart daily={r.daily} days={r.window.days} />
          <Localities localities={r.localities} minCell={r.min_cell} />
        </div>
      )}
    </>
  );
}

function weekly(daily: ReportsData["daily"]) {
  const out: { date: string; readings: number; flags: number; days: number }[] = [];
  for (const d of daily) {
    const day = new Date(d.date);
    const monday = new Date(day);
    monday.setDate(day.getDate() - ((day.getDay() + 6) % 7));
    const key = monday.toISOString().slice(0, 10);
    const last = out[out.length - 1];
    if (last && last.date === key) {
      last.readings += d.readings;
      last.flags += d.flags;
      last.days += 1;
    } else out.push({ date: key, readings: d.readings, flags: d.flags, days: 1 });
  }
  return out;
}

function ReadingsChart({ daily, days }: { daily: ReportsData["daily"]; days: number }) {
  const [group, setGroup] = useState<"day" | "week">(days > 60 ? "week" : "day");
  const by = days <= 7 ? "day" : group;
  const data = useMemo(
    () => (by === "week" ? weekly(daily) : daily.map((d) => ({ ...d, days: 1 }))).map((d) => ({ ...d, normal: d.readings - d.flags })),
    [daily, by],
  );
  const avg = data.length ? data.reduce((a, d) => a + d.readings, 0) / data.length : 0;
  const peak = data.reduce<(typeof data)[number] | null>((a, d) => (!a || d.readings > a.readings ? d : a), null);
  const unit = by === "week" ? "week" : "day";

  return (
    <Card
      title={`Readings per ${unit}`}
      aside={days > 7 && <Chips label="Group by" value={by} onChange={setGroup} options={[{ id: "day", label: "Daily" }, { id: "week", label: "Weekly" }]} />}
    >
      {data.every((d) => d.readings === 0) ? (
        <Empty title="No readings in this period" />
      ) : (
        <>
          <p className="mb-4 text-sm text-ink-soft">
            Average <strong className="text-ink">{avg.toFixed(1)}</strong> a {unit}
            {peak && peak.readings > 0 && (
              <>
                {" "}· busiest {by === "week" ? `week of ${fmtShortDay(peak.date)}` : fmtShortDay(peak.date)} with <strong className="text-ink">{peak.readings}</strong>
              </>
            )}
          </p>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={data} margin={{ top: 12, right: 16, bottom: 24, left: 8 }} barCategoryGap={by === "week" ? "25%" : 2}>
                <CartesianGrid stroke={AXIS.line} strokeDasharray="3 4" vertical={false} />
                <XAxis dataKey="date" tickFormatter={fmtShortDay} tick={AXIS.tick} tickLine={false} axisLine={{ stroke: AXIS.line }} minTickGap={24}>
                  <Label value={by === "week" ? "Week starting (Monday)" : "Date"} position="insideBottom" offset={-14} style={AXIS.label} />
                </XAxis>
                <YAxis allowDecimals={false} tick={AXIS.tick} axisLine={false} tickLine={false} width={48}>
                  <Label value="Readings" angle={-90} position="insideLeft" style={{ ...AXIS.label, textAnchor: "middle" }} />
                </YAxis>
                {avg > 0 && <ReferenceLine y={avg} stroke={AXIS.ink} strokeDasharray="5 4" />}
                <Tooltip
                  cursor={{ fill: "rgb(var(--hn-ink) / 0.05)" }}
                  content={({ active, payload }) => {
                    const d = active && (payload?.[0]?.payload as (typeof data)[number] | undefined);
                    if (!d) return null;
                    return (
                      <TipBox title={by === "week" ? `Week of ${fmtDate(d.date)}${d.days < 7 ? ` (${plural(d.days, "day")})` : ""}` : fmtDate(d.date)}>
                        <TipRow label="Readings" value={d.readings} />
                        <TipRow color={NORMAL} label="Normal" value={d.normal} />
                        <TipRow color={FLAG_RED} label="Flagged" value={d.flags} />
                        <TipRow label="Flag rate" value={pct(d.flags, d.readings)} />
                      </TipBox>
                    );
                  }}
                />
                <Bar dataKey="normal" stackId="r" fill={NORMAL} maxBarSize={40} isAnimationActive={false} />
                <Bar dataKey="flags" stackId="r" fill={FLAG_RED} maxBarSize={40} radius={[3, 3, 0, 0]} isAnimationActive={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <Legend
            items={[
              { color: NORMAL, label: "Normal readings" },
              { color: FLAG_RED, label: "Flagged readings" },
              { color: AXIS.ink, label: `Average per ${unit}`, dashed: true },
            ]}
          />
        </>
      )}
    </Card>
  );
}

function Localities({ localities, minCell }: { localities: Locality[]; minCell: number }) {
  const [sort, setSort] = useState<Sort>("readings");
  const rows = useMemo(() => {
    const by = SORTS.find((s) => s.id === sort)!.by;
    return [...localities].sort((a, b) => by(b) - by(a));
  }, [localities, sort]);
  const top = rows.slice(0, 8).map((l) => ({ ...l, normal: l.readings - l.flags }));
  const maxCitizens = Math.max(1, ...localities.map((l) => l.citizens));

  return (
    <Card title="By locality" aside={<span className="text-xs text-ink-soft">Areas under {minCell} citizens are grouped as "Other localities"</span>}>
      {localities.length === 0 ? (
        <Empty title="No localities yet" />
      ) : (
        <>
          <div className="mb-5">
            <Chips label="Sort by" value={sort} onChange={setSort} options={SORTS.map((s) => ({ id: s.id, label: s.label }))} />
          </div>
          <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)]">
            <div>
              <div style={{ height: Math.max(160, top.length * 40 + 48) }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={top} layout="vertical" margin={{ top: 0, right: 24, bottom: 20, left: 8 }} barCategoryGap="28%">
                    <CartesianGrid stroke={AXIS.line} strokeDasharray="3 4" horizontal={false} />
                    <XAxis type="number" allowDecimals={false} tick={AXIS.tick} tickLine={false} axisLine={{ stroke: AXIS.line }}>
                      <Label value="Readings" position="insideBottom" offset={-12} style={AXIS.label} />
                    </XAxis>
                    <YAxis type="category" dataKey="locality" width={120} tick={{ ...AXIS.tick, fill: "rgb(var(--hn-ink))" }} tickLine={false} axisLine={false} />
                    <Tooltip
                      cursor={{ fill: "rgb(var(--hn-ink) / 0.05)" }}
                      content={({ active, payload }) => {
                        const l = active && (payload?.[0]?.payload as (typeof top)[number] | undefined);
                        if (!l) return null;
                        return (
                          <TipBox title={l.locality}>
                            <TipRow color={NORMAL} label="Normal" value={l.normal} />
                            <TipRow color={FLAG_RED} label="Flagged" value={l.flags} />
                            <TipRow label="Flag rate" value={pct(l.flags, l.readings)} />
                            <TipRow label="Submitted" value={`${l.submitting} of ${l.citizens}`} />
                          </TipBox>
                        );
                      }}
                    />
                    <Bar dataKey="normal" stackId="l" fill={NORMAL} isAnimationActive={false} />
                    <Bar dataKey="flags" stackId="l" fill={FLAG_RED} radius={[0, 3, 3, 0]} isAnimationActive={false} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <Legend
                items={[
                  { color: NORMAL, label: "Normal readings" },
                  { color: FLAG_RED, label: "Flagged readings" },
                ]}
              />
              {rows.length > top.length && <p className="mt-1 text-xs text-ink-muted">Chart shows the top {top.length}; the table has all {rows.length}.</p>}
            </div>
            <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Readings by locality">
              <table className="w-full min-w-[520px] text-left text-sm">
                <thead className="border-b border-line text-xs font-semibold uppercase tracking-[0.06em] text-ink-soft">
                  <tr>
                    <th className="py-2.5 pr-3 font-semibold">Locality</th>
                    <th className="px-3 py-2.5 font-semibold">Citizens submitting</th>
                    <th className="px-3 py-2.5 text-right font-semibold">Readings</th>
                    <th className="px-3 py-2.5 text-right font-semibold">Flagged</th>
                    <th className="py-2.5 pl-3 text-right font-semibold">Flag rate</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line tabular-nums">
                  {rows.map((l) => (
                    <tr key={l.locality} className="hover:bg-paper">
                      <td className="py-3 pr-3 font-medium text-ink">{l.locality}</td>
                      <td className="px-3 py-3">
                        <span className="flex items-center gap-2">
                          <span className="relative h-2 w-20 overflow-hidden rounded-full bg-paper-raised" title={`${l.citizens} citizens`}>
                            <span className="absolute inset-y-0 left-0 rounded-full bg-ink/15" style={{ width: `${(l.citizens / maxCitizens) * 100}%` }} />
                            <span className="absolute inset-y-0 left-0 rounded-full bg-blue-600" style={{ width: `${(l.submitting / maxCitizens) * 100}%` }} />
                          </span>
                          <span className="text-ink">
                            {l.submitting} <span className="text-ink-soft">of {l.citizens}</span>
                          </span>
                        </span>
                      </td>
                      <td className="px-3 py-3 text-right text-ink">{l.readings}</td>
                      <td className={cx("px-3 py-3 text-right", l.flags ? "font-semibold text-red-700" : "text-ink-soft")}>{l.flags}</td>
                      <td className="py-3 pl-3 text-right text-ink">{pct(l.flags, l.readings)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </Card>
  );
}
