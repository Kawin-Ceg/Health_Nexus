import { useEffect, useRef } from "react";
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
  low: "border-l-line",
};

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

  return (
    <div className="flex flex-col gap-6">
      <Card title={t("alerts.alerts")}>
        {alerts.length === 0 ? (
          <Empty title={t("alerts.none")} />
        ) : (
          <ul className="flex flex-col gap-2">
            {alerts.map((a) => (
              <li key={a.id} className={cx("rounded-xl border border-line border-l-4 bg-surface p-3 text-sm", TONE[a.severity])}>
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="text-ink">{a.message}</p>
                  {!a.is_read && <span className="rounded-full bg-brand-soft px-2 text-xs font-semibold text-brand">{t("alerts.new")}</span>}
                </div>
                <p className="mt-1 text-xs text-ink-soft">{fmtDateTime(a.created_at)}</p>
              </li>
            ))}
          </ul>
        )}
      </Card>
      {advisories.length > 0 && (
        <Card title={t("alerts.advisories")}>
          <ul className="flex flex-col gap-3">
            {advisories.map((a) => (
              <li key={a.id} className={cx("flex gap-3 rounded-xl border border-line border-l-4 bg-surface p-3 text-sm", TONE[a.severity])}>
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
      )}
    </div>
  );
}
