import { AlertList } from "../components/app/AlertList";
import { ErrorNote, Loading, PageHeader } from "../components/app/ui";
import { useResource } from "../lib/useResource";
import { getAlerts } from "../services/health";

/** A worker's own notifications: bookings, changes, visits that need an outcome. */
export function Notifications() {
  const { data, error, reload } = useResource((signal) => getAlerts(signal), "notifications");
  if (error) return <ErrorNote message={error} onRetry={reload} />;
  if (!data) return <Loading />;
  return (
    <>
      <PageHeader title="Notifications" lead="Visits you booked, changes to them, and visits waiting for an outcome." />
      <AlertList alerts={data.alerts} advisories={data.advisories} />
    </>
  );
}
