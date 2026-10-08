import type { BaselineStatus, Metric, VitalCheck } from "../../services/health";
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

const STAGE_TEXT = { learning: "Learning", blending: "Getting to know you", personal: "Personal" } as const;

/**
 * Per vital: how far the model has come from published normal ranges to the
 * citizen's own baseline. The bar fills from 0 to `full_readings` readings.
 */
export function BaselineProgress({ status, metrics }: { status: BaselineStatus; metrics: Map<string, Metric> }) {
  return (
    <ul className="flex flex-col gap-4">
      {status.vitals.map((v) => {
        const m = metrics.get(v.key);
        if (!m) return null;
        const filled = Math.min(100, Math.round((v.readings / status.full_readings) * 100));
        const usual = v.baseline !== null && v.spread !== null ? `usual ${fmt(m, v.baseline)} ± ${fmt(m, v.spread)} ${m.unit}` : null;
        let detail: string;
        if (v.stage === "learning") {
          detail = `${v.readings_to_start} more reading${v.readings_to_start === 1 ? "" : "s"} until we start learning your normal`;
        } else if (v.stage === "blending") {
          detail = `${usual} · ${Math.round(v.weight * 100)}% based on you · ${v.readings_to_full} more to be fully personal`;
        } else {
          detail = `${usual} · judged against your own readings`;
        }
        return (
          <li key={v.key}>
            <div className="mb-1 flex flex-wrap items-baseline justify-between gap-2 text-sm">
              <span className="font-medium text-ink">{m.label}</span>
              <span className={cx("text-xs font-semibold", v.stage === "personal" ? "text-success" : "text-ink-soft")}>{STAGE_TEXT[v.stage]}</span>
            </div>
            <div
              className="h-2 overflow-hidden rounded-full bg-paper-raised"
              role="progressbar"
              aria-label={`${m.label}: ${v.readings} of ${status.full_readings} readings`}
              aria-valuemin={0}
              aria-valuemax={status.full_readings}
              aria-valuenow={Math.min(v.readings, status.full_readings)}
            >
              <div className={cx("h-full rounded-full", v.stage === "personal" ? "bg-success" : "bg-brand")} style={{ width: `${filled}%` }} />
            </div>
            <p className="mt-1 text-xs text-ink-soft">{detail}</p>
          </li>
        );
      })}
    </ul>
  );
}
