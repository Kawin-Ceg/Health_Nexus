import { Link } from "react-router-dom";
import { Card, ErrorNote, Loading, PageHeader, Stat } from "../../components/app/ui";
import { paths } from "../../lib/routes";
import { useResource } from "../../lib/useResource";
import { getOverview } from "../../services/admin";

export function AdminDashboard() {
  const res = useResource((s) => getOverview(s), "overview");
  const o = res.data;

  return (
    <>
      <PageHeader title="Admin console" lead="Approve health workers, look after accounts and answer support concerns." />
      {res.error && <ErrorNote message={res.error} onRetry={res.reload} />}
      {!o ? (
        !res.error && <Loading />
      ) : (
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat label="Pending applications" value={o.pending_applications} tone={o.pending_applications ? "warn" : undefined} hint={<Link className="text-brand underline" to={paths.adminApplications}>Review</Link>} />
            <Stat label="Open concerns" value={o.open_concerns} tone={o.open_concerns ? "warn" : undefined} hint={<Link className="text-brand underline" to={paths.adminConcerns}>Answer</Link>} />
            <Stat label="Workers with no centre" value={o.workers_without_facility} tone={o.workers_without_facility ? "danger" : undefined} hint="They see no citizens" />
            <Stat label="Open flags" value={o.open_flags} hint="Across every centre" />
          </div>
          <Card title="Accounts">
            <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
              <Stat label="Citizens" value={o.users_by_role.user} />
              <Stat label="PHC workers" value={o.users_by_role.phc_worker} />
              <Stat label="Awaiting approval" value={o.users_by_role.pending_phc} />
              <Stat label="Administrators" value={o.users_by_role.admin} />
              <Stat label="Deactivated" value={o.inactive_accounts} />
              <Stat label="Email not confirmed" value={o.unverified_accounts} />
            </div>
          </Card>
          <Card title="Activity, last 7 days">
            <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
              <Stat label="Readings logged" value={o.readings_last_7_days} />
              <Stat label="Assistant questions" value={o.assistant_questions_last_7_days} />
              <Stat label="Active health centres" value={o.facilities_active} />
            </div>
          </Card>
        </div>
      )}
    </>
  );
}
