import { Area, CartesianGrid, ComposedChart, Label, Line, ReferenceArea, ResponsiveContainer, Tooltip, XAxis, YAxis, type DotProps } from "recharts";
import { fmtDateTime, fmtShortDay } from "../../lib/format";
import type { Metric } from "../../services/health";

export interface TrendPoint {
  measured_at: string;
  value: number;
  flagged: boolean;
}

const INK_SOFT = "rgb(var(--hn-ink-soft))";
const LINE = "rgb(var(--hn-line))";
const BRAND = "rgb(var(--hn-forest))";

function outsideOf(metric: Metric, v: number) {
  return !!metric.normal && (v < metric.normal[0] || v > metric.normal[1]);
}

function PointDot(props: DotProps & { payload?: TrendPoint; metric: Metric }) {
  const { cx, cy, payload, metric } = props;
  if (cx === undefined || cy === undefined || !payload) return null;
  if (payload.flagged) return <circle cx={cx} cy={cy} r={6} fill="#dc2626" stroke="rgb(var(--hn-surface))" strokeWidth={2} />;
  if (outsideOf(metric, payload.value)) return <circle cx={cx} cy={cy} r={4.5} fill="#d97706" stroke="rgb(var(--hn-surface))" strokeWidth={2} />;
  return <circle cx={cx} cy={cy} r={3.5} fill={BRAND} stroke="rgb(var(--hn-surface))" strokeWidth={1.5} />;
}

export function TrendChart({ metric, points, height = 320 }: { metric: Metric; points: TrendPoint[]; height?: number }) {
  const values = points.map((p) => p.value);
  const lows = [...values, ...(metric.normal ? [metric.normal[0]] : [])];
  const highs = [...values, ...(metric.normal ? [metric.normal[1]] : [])];
  const pad = (Math.max(...highs) - Math.min(...lows)) * 0.15 || 1;
  const domain: [number, number] = [
    Math.max(metric.plausible[0], Math.floor(Math.min(...lows) - pad)),
    Math.min(metric.plausible[1], Math.ceil(Math.max(...highs) + pad)),
  ];
  const gradient = `trend-${metric.key}`;

  return (
    <figure>
      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={points} margin={{ top: 12, right: 16, bottom: 4, left: 12 }}>
            <defs>
              <linearGradient id={gradient} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={BRAND} stopOpacity={0.22} />
                <stop offset="100%" stopColor={BRAND} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke={LINE} strokeDasharray="3 4" vertical={false} />
            {metric.normal && (
              <ReferenceArea y1={metric.normal[0]} y2={metric.normal[1]} fill="#16a34a" fillOpacity={0.09} stroke="#16a34a" strokeOpacity={0.35} strokeDasharray="4 4">
                <Label value="Normal range" position="insideTopRight" fill="#15803d" fontSize={12} fontWeight={600} />
              </ReferenceArea>
            )}
            <XAxis
              dataKey="measured_at"
              tickFormatter={fmtShortDay}
              tick={{ fill: INK_SOFT, fontSize: 12 }}
              axisLine={{ stroke: LINE }}
              tickLine={false}
              minTickGap={28}
            />
            <YAxis domain={domain} tick={{ fill: INK_SOFT, fontSize: 12 }} axisLine={false} tickLine={false} width={56}>
              <Label value={metric.unit} angle={-90} position="insideLeft" offset={-2} fill={INK_SOFT} fontSize={12} fontWeight={600} style={{ textAnchor: "middle" }} />
            </YAxis>
            <Tooltip
              cursor={{ stroke: INK_SOFT, strokeWidth: 1, strokeDasharray: "3 3" }}
              content={({ active, payload }) => {
                const p = active && (payload?.[0]?.payload as TrendPoint | undefined);
                if (!p) return null;
                const off = outsideOf(metric, p.value);
                return (
                  <div className="rounded-xl border border-line bg-surface px-3 py-2 text-xs shadow-[var(--hn-shadow-md)]">
                    <p className="text-ink-soft">{fmtDateTime(p.measured_at)}</p>
                    <p className="mt-0.5 text-sm font-semibold text-ink">
                      {p.value.toFixed(metric.decimals)} {metric.unit}
                    </p>
                    {p.flagged ? (
                      <p className="font-semibold text-red-700">Flagged</p>
                    ) : off ? (
                      <p className="font-semibold text-amber-700">Outside normal</p>
                    ) : metric.normal ? (
                      <p className="text-green-700">Within normal</p>
                    ) : null}
                  </div>
                );
              }}
            />
            <Area type="monotone" dataKey="value" stroke="none" fill={`url(#${gradient})`} isAnimationActive={false} />
            <Line
              type="monotone"
              dataKey="value"
              stroke={BRAND}
              strokeWidth={2.5}
              dot={<PointDot metric={metric} />}
              activeDot={{ r: 7, stroke: "rgb(var(--hn-surface))", strokeWidth: 2 }}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-ink-soft">
        <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full" style={{ background: BRAND }} /> Reading</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-amber-600" /> Outside normal</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-3 w-3 rounded-full bg-red-600" /> Flagged</span>
        {metric.normal && (
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2.5 w-4 rounded-sm border border-dashed border-green-600 bg-green-600/10" /> Normal {metric.normal[0]}–{metric.normal[1]} {metric.unit}
          </span>
        )}
      </figcaption>
    </figure>
  );
}
