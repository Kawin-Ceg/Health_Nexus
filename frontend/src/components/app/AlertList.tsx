import { useEffect, useMemo, useRef, useState } from "react";
import { Megaphone } from "lucide-react";
import { useT } from "../../i18n";
import { fmtDateTime } from "../../lib/format";
import { play } from "../../lib/sound";
import type { Advisory } from "../../services/advisories";
import { markRead, type AlertItem } from "../../services/health";
import { Card, Empty, cx } from "./ui";

const TONE: Record<AlertItem["severity"], string> = {
  high: "border-l-sev-high",
  medium: "border-l-sev-moderate",
  low: "border-l-line-strong/40",
};

const RECENT = 5;

/**
 * Personal alerts, then community advisories. Unread ones stay marked "New" for
 * this visit, and are marked read on the server once shown, which clears the badge.
 */
export function AlertList({ alerts, advisories }: { alerts: AlertItem[]; advisories: Advisory[] }) {
  const t = useT();
  const sent = useRef(false);
  useEffect(() => {
    const unread = alerts.filter((a) => !a.is_read).map((a) => a.id);
    if (unread.length && !sent.current) {
      sent.current = true;
      void markRead(unread)
        .then(() => play("clear"))
        .catch(() => undefined);
    }
  }, [alerts]);

  const [month, setMonth] = useState("recent");
  const months = useMemo(() => {
    const seen = new Map<string, string>();
    for (const a of alerts) {
      const d = new Date(a.created_at);
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
      if (!seen.has(key)) seen.set(key, d.toLocaleDateString("en-IN", { month: "long", year: "numeric" }));
    }
    return [...seen.entries()];
  }, [alerts]);
  const shown =
    month === "recent"
      ? alerts.slice(0, RECENT)
      : alerts.filter((a) => {
          const d = new Date(a.created_at);
          return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}` === month;
        });

  return (
    <div className="flex flex-col gap-6">
      <Card
        title={t("alerts.alerts")}
        aside={
          alerts.length > 0 && (
            <select
              aria-label="Show alerts from"
              value={month}
              onChange={(e) => setMonth(e.target.value)}
              className="min-h-10 rounded-full border border-line bg-surface px-4 text-sm"
            >
              <option value="recent">Most recent</option>
              {months.map(([key, name]) => (
                <option key={key} value={key}>{name}</option>
              ))}
            </select>
          )
        }
      >
        {shown.length === 0 ? (
          <Empty title={t("alerts.none")} />
        ) : (
          <ul className="flex flex-col gap-3">
            {shown.map((a) => (
              <li key={a.id} className={cx("rounded-2xl border border-line border-l-4 bg-surface p-4 text-sm", TONE[a.severity])}>
                <p className="text-ink">{a.message}</p>
                <p className="mt-2 flex items-center gap-2 text-xs text-ink-soft">
                  {fmtDateTime(a.created_at)}
                  {!a.is_read && <span className="rounded-full bg-brand-soft px-2 font-semibold text-brand">{t("alerts.new")}</span>}
                </p>
              </li>
            ))}
          </ul>
        )}
        {month === "recent" && alerts.length > RECENT && (
          <p className="mt-3 text-xs text-ink-muted">Showing the {RECENT} newest of {alerts.length}. Pick a month to see older ones.</p>
        )}
      </Card>
      {advisories.length > 0 && <AdvisoryList advisories={advisories} />}
    </div>
  );
}

export function AdvisoryList({ advisories }: { advisories: Advisory[] }) {
  const t = useT();
  return (
    <Card title={t("alerts.advisories")}>
      <ul className="flex flex-col gap-3">
        {advisories.map((a) => (
          <li key={a.id} className={cx("flex gap-3 rounded-2xl border border-line border-l-4 bg-surface p-4 text-sm", TONE[a.severity])}>
            <Megaphone size={18} className="mt-0.5 shrink-0 text-accent-ink" aria-hidden="true" />
            <div>
              <p className="font-semibold text-ink">{a.title}</p>
              <p className="whitespace-pre-line text-ink">{a.body}</p>
              <p className="mt-1 text-xs text-ink-soft">
                {a.audience} · {fmtDateTime(a.created_at)}
              </p>
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}
