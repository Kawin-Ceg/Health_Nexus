import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { workerState } from "../../components/app/phc";
import { Card, Loading, PageHeader, Stat } from "../../components/app/ui";
import { fmtDate, fmtShortDay } from "../../lib/format";
import { oneOf, useQueryState } from "../../lib/params";
import { useResource } from "../../lib/useResource";
import { getReports, type Reports as ReportsData } from "../../services/phc";

const WINDOWS = ["7", "30", "90", "180"] as const;
const INK_SOFT = "rgb(var(--hn-ink-soft))";

/** Aggregates only. No names, and small localities are folded together so no one can be picked out. */
export function Reports() {
  const { params, set } = useQueryState();
  const days = Number(oneOf(params.get("days"), WINDOWS, "30"));
  const rep = useResource((s) => getReports(days, s), String(days));
  const blocked = workerState(rep);
  if (blocked) return blocked;
  const r = rep.data;

  return (
    <>
      <PageHeader
        title="Reports"
        lead={r ? `${fmtDate(r.window.start)} – ${fmtDate(r.window.end)} (whole days, India time).` : undefined}
        actions={
          <select aria-label="Period" value={String(days)} onChange={(e) => set({ days: e.target.value })} className="min-h-11 rounded-2xl border border-line bg-surface px-3 text-sm">
            {WINDOWS.map((w) => <option key={w} value={w}>Last {w} days</option>)}
          </select>
        }
      />
      {!r ? <Loading /> : (
        <>
          <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat label={`Readings, last ${r.window.days} days`} value={r.readings} />
            <Stat label={`Citizens who submitted, last ${r.window.days} days`} value={r.citizens_submitting} />
            <Stat label={`Flagged, last ${r.window.days} days`} value={r.flags} hint={r.flag_rate === null ? undefined : `${(r.flag_rate * 100).toFixed(1)}% of readings`} />
            <Stat label="Citizens in catchment (today)" value={r.catchment_now} />
          </div>

          <Card className="mb-6" title="Readings per day">
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={r.daily} margin={{ top: 8, right: 8, bottom: 0, left: -16 }} barCategoryGap={2}>
                  <CartesianGrid vertical={false} stroke="rgb(var(--hn-line))" />
                  <XAxis dataKey="date" tickFormatter={fmtShortDay} tick={{ fill: INK_SOFT, fontSize: 12 }} tickLine={false} axisLine={{ stroke: "rgb(var(--hn-line))" }} minTickGap={24} />
                  <YAxis allowDecimals={false} tick={{ fill: INK_SOFT, fontSize: 12 }} axisLine={false} tickLine={false} />
                  <Tooltip
                    cursor={{ fill: "rgb(var(--hn-ink) / 0.05)" }}
                    content={({ active, payload }) => {
                      const d = active && (payload?.[0]?.payload as ReportsData["daily"][number] | undefined);
                      if (!d) return null;
                      return (
                        <div className="rounded-xl border border-line bg-surface px-3 py-2 text-xs shadow-[var(--hn-shadow-md)]">
                          <p className="text-ink-soft">{fmtDate(d.date)}</p>
                          <p className="text-ink"><strong>{d.readings}</strong> readings, {d.flags} flagged</p>
                        </div>
                      );
                    }}
                  />
                  <Bar dataKey="readings" fill="rgb(var(--hn-brand))" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <Card title="By locality" aside={<span className="text-xs text-ink-soft">Localities with fewer than {r.min_cell} citizens are grouped as "Other localities".</span>}>
            <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Flags by locality">
              <table className="w-full min-w-[520px] text-left text-sm">
                <thead className="text-xs uppercase tracking-wide text-ink-soft">
                  <tr>
                    <th className="py-2 font-medium">Locality</th>
                    <th className="py-2 text-right font-medium">Citizens (today)</th>
                    <th className="py-2 text-right font-medium">Submitted</th>
                    <th className="py-2 text-right font-medium">Readings</th>
                    <th className="py-2 text-right font-medium">Flagged</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line tabular-nums">
                  {r.localities.map((l) => (
                    <tr key={l.locality}>
                      <td className="py-2 text-ink">{l.locality}</td>
                      <td className="py-2 text-right text-ink">{l.citizens}</td>
                      <td className="py-2 text-right text-ink">{l.submitting}</td>
                      <td className="py-2 text-right text-ink">{l.readings}</td>
                      <td className="py-2 text-right text-ink">{l.flags}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </>
  );
}
