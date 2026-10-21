import { CartesianGrid, Line, LineChart, ReferenceArea, ResponsiveContainer, Tooltip, XAxis, YAxis, type DotProps } from "recharts";
import { fmtDateTime, fmtShortDay } from "../../lib/format";
import type { Metric } from "../../services/health";

export interface TrendPoint {
  measured_at: string;
  value: number;
  flagged: boolean;
}

const INK_SOFT = "rgb(var(--hn-ink-soft))";
const LINE = "rgb(var(--hn-line))";

function FlagDot(props: DotProps & { payload?: TrendPoint }) {
  const { cx, cy, payload } = props;
  if (cx === undefined || cy === undefined || !payload) return null;
  return payload.flagged ? (
    <circle cx={cx} cy={cy} r={5} fill="rgb(var(--hn-sev-critical))" stroke="rgb(var(--hn-surface))" strokeWidth={2} />
  ) : (
    <circle cx={cx} cy={cy} r={3} fill="rgb(var(--hn-brand))" stroke="rgb(var(--hn-surface))" strokeWidth={2} />
  );
}

/**
 * One vital over time. Single series, so no legend: the heading names it.
 * The shaded band is the published normal range; flagged readings are larger
 * dots and say "flagged" in the tooltip, so colour is never the only signal.
 */
export function TrendChart({ metric, points, height = 240 }: { metric: Metric; points: TrendPoint[]; height?: number }) {
  const values = points.map((p) => p.value);
  const lows = [...values, ...(metric.normal ? [metric.normal[0]] : [])];
  const highs = [...values, ...(metric.normal ? [metric.normal[1]] : [])];
  const pad = (Math.max(...highs) - Math.min(...lows)) * 0.15 || 1;
  const domain: [number, number] = [
    Math.max(metric.plausible[0], Math.floor(Math.min(...lows) - pad)),
    Math.min(metric.plausible[1], Math.ceil(Math.max(...highs) + pad)),
  ];

  return (
    <figure>
      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points} margin={{ top: 8, right: 12, bottom: 0, left: -8 }}>
            <CartesianGrid stroke={LINE} strokeDasharray="0" vertical={false} />
            {metric.normal && (
              <ReferenceArea y1={metric.normal[0]} y2={metric.normal[1]} fill="rgb(var(--hn-success))" fillOpacity={0.08} strokeOpacity={0} />
            )}
            <XAxis
              dataKey="measured_at"
              tickFormatter={fmtShortDay}
              tick={{ fill: INK_SOFT, fontSize: 12 }}
              axisLine={{ stroke: LINE }}
              tickLine={false}
              minTickGap={24}
            />
            <YAxis domain={domain} tick={{ fill: INK_SOFT, fontSize: 12 }} axisLine={false} tickLine={false} width={48} />
            <Tooltip
              cursor={{ stroke: INK_SOFT, strokeWidth: 1 }}
              content={({ active, payload }) => {
                const p = active && payload?.[0]?.payload as TrendPoint | undefined;
                if (!p) return null;
                return (
                  <div className="rounded-xl border border-line bg-surface px-3 py-2 text-xs shadow-[var(--hn-shadow-md)]">
                    <p className="text-ink-soft">{fmtDateTime(p.measured_at)}</p>
                    <p className="font-semibold text-ink">
                      {p.value.toFixed(metric.decimals)} {metric.unit}
                      {p.flagged && <span className="ml-2 text-sev-critical">flagged</span>}
                    </p>
                  </div>
                );
              }}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="rgb(var(--hn-brand))"
              strokeWidth={2}
              dot={<FlagDot />}
              activeDot={{ r: 6 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="mt-2 text-xs text-ink-soft">
        {metric.normal ? `Shaded: normal range ${metric.normal[0]}–${metric.normal[1]} ${metric.unit}. ` : ""}
        Larger red dots are flagged readings.
      </figcaption>
    </figure>
  );
}
