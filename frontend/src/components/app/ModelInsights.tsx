import type { Metric, VitalCheck } from "../../services/health";
import { cx } from "./ui";

type Audience = "citizen" | "worker";

const fmt = (m: Metric, v: number) => v.toFixed(m.decimals);

function comparedWith(c: VitalCheck, m: Metric, who: Audience): string {
  const usual = c.baseline !== null && c.spread !== null ? `${fmt(m, c.baseline)} ± ${fmt(m, c.spread)} ${m.unit}` : null;
  const range = m.normal ? `normal range ${fmt(m, m.normal[0])}–${fmt(m, m.normal[1])} ${m.unit}` : "no published range";
  const their = who === "citizen" ? "your" : "their";
  if (c.stage === "learning" || !usual) return range.charAt(0).toUpperCase() + range.slice(1);
  if (c.stage === "personal") return `${their.charAt(0).toUpperCase() + their.slice(1)} usual ${usual}`;
  return `${their.charAt(0).toUpperCase() + their.slice(1)} usual ${usual} (${Math.round(c.weight * 100)}%) and the ${range}`;
}

function verdict(c: VitalCheck, who: Audience): { text: string; cls: string } {
  if (c.safety) return { text: "Past a safety limit", cls: "font-semibold text-sev-high" };
  if (c.contribution > 0) return { text: "Unusual", cls: "font-semibold text-sev-high" };
  if (!c.confirmed) {
    return { text: who === "citizen" ? "Unusual for you, watching the next reading" : "Unusual for them, unconfirmed", cls: "text-warn" };
  }
  return { text: "As expected", cls: "text-success" };
}

/**
 * How the anomaly model judged each vital of one reading: what it was compared
 * with (published range, the person's own baseline, or a blend of both) and the
 * outcome. Shared by the citizen's result screen and the worker's record page.
 */
export function ScoreBreakdown({ checks, metrics, who }: { checks: VitalCheck[]; metrics: Map<string, Metric>; who: Audience }) {
  if (checks.length === 0) return null;
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[460px] text-left text-sm">
        <thead className="text-xs uppercase tracking-wide text-ink-soft">
          <tr>
            <th className="py-2 font-medium">Vital</th>
            <th className="py-2 font-medium">Value</th>
            <th className="py-2 font-medium">Compared with</th>
            <th className="py-2 font-medium">Result</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {checks.map((c) => {
            const m = metrics.get(c.key);
            if (!m) return null;
            const v = verdict(c, who);
            return (
              <tr key={c.key}>
                <td className="py-2 text-ink">{m.label}</td>
                <td className="py-2 tabular-nums text-ink">
                  {fmt(m, c.value)} {m.unit}
                </td>
                <td className="py-2 text-ink-soft">{comparedWith(c, m, who)}</td>
                <td className={cx("py-2", v.cls)}>{v.text}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/** "Compared with their baseline" or "normal ranges", for a flag. Null for flags scored before the model stored it. */
export function BasisTag({ basis }: { basis: string | null }) {
  if (!basis) return null;
  const personal = basis === "personal_baseline";
  return (
    <span
      className={cx("rounded-full px-2 py-0.5 text-xs font-medium", personal ? "bg-paper-raised text-brand" : "bg-paper-raised text-ink-soft")}
      title={personal ? "Judged against this person's own usual readings" : "Judged against published normal ranges"}
    >
      {personal ? "vs their baseline" : "vs normal range"}
    </span>
  );
}

