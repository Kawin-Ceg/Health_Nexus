import { CalendarClock } from "lucide-react";
import { AlertList } from "../../components/app/AlertList";
import { Card, ErrorNote, Loading, PageHeader, VisitBadge } from "../../components/app/ui";
import { fmtVisit } from "../../lib/format";
import { useResource } from "../../lib/useResource";
import { useT } from "../../i18n";
import { getAlerts, getMySchedule, type Visit, type VisitState } from "../../services/health";

// Sections by derived state. A visit whose time has passed is never "upcoming":
// due_now (just passed, within the grace window) needs attention too.
const ATTENTION: VisitState[] = ["due_now", "overdue", "missed"];
const UPCOMING: VisitState[] = ["today", "upcoming"];
const RECENT_MISSED_DAYS = 30;

function VisitRow({ visit }: { visit: Visit }) {
  const t = useT();
  return (
    <li className="flex flex-wrap items-start gap-3 rounded-xl border border-line p-3 text-sm">
      <CalendarClock size={18} className="mt-0.5 shrink-0 text-brand" aria-hidden="true" />
      <div className="flex-1">
        <p className="font-semibold text-ink">{fmtVisit(visit.scheduled_for)}</p>
        <p className="text-ink-soft">
          {visit.worker_name ? t("alerts.with", { name: visit.worker_name }) : t("alerts.centreVisit")}
          {visit.location ? ` · ${visit.location}` : ""}
        </p>
        {visit.reason && <p className="text-ink-soft">{visit.reason}</p>}
        {visit.state === "overdue" && <p className="mt-1 text-danger">{t("alerts.overdue")}</p>}
        {visit.state === "due_now" && <p className="mt-1 text-warn">{t("alerts.dueNow")}</p>}
      </div>
      <VisitBadge state={visit.state} />
    </li>
  );
}

function Section({ title, visits, empty }: { title: string; visits: Visit[]; empty: string }) {
  return (
    <Card title={title}>
      {visits.length === 0 ? (
        <p className="text-sm text-ink-soft">{empty}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {visits.map((v) => (
            <VisitRow key={v.id} visit={v} />
          ))}
        </ul>
      )}
    </Card>
  );
}

export function CitizenAlerts() {
  const t = useT();
  const { data, error, reload } = useResource((signal) => Promise.all([getMySchedule(signal), getAlerts(signal)]), "alerts");
  if (error) return <ErrorNote message={error} onRetry={reload} />;
  if (!data) return <Loading />;
  const [visits, alerts] = data;

  const cutoff = Date.now() - RECENT_MISSED_DAYS * 86400_000;
  const recent = (v: Visit) => v.state !== "missed" || new Date(v.scheduled_for).getTime() >= cutoff;
  const byTime = (a: Visit, b: Visit) => a.scheduled_for.localeCompare(b.scheduled_for);
  const attention = visits.filter((v) => ATTENTION.includes(v.state) && recent(v)).sort(byTime);
  const upcoming = visits.filter((v) => UPCOMING.includes(v.state)).sort(byTime);
  const past = visits.filter((v) => !attention.includes(v) && !upcoming.includes(v));

  return (
    <>
      <PageHeader title={t("alerts.title")} lead={t("alerts.lead")} />
      <div className="grid items-start gap-6 lg:grid-cols-2">
        <div className="flex flex-col gap-6">
          {attention.length > 0 && <Section title={t("alerts.attention")} visits={attention} empty="" />}
          <Section title={t("alerts.upcoming")} visits={upcoming} empty={t("alerts.noVisits")} />
          {past.length > 0 && <Section title={t("alerts.past")} visits={past} empty="" />}
        </div>
        <AlertList alerts={alerts.alerts} advisories={alerts.advisories} />
      </div>
    </>
  );
}
