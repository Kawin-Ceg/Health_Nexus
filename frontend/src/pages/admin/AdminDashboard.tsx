import { useState } from "react";
import { Link } from "react-router-dom";
import { BadgeCheck, Download, LifeBuoy, ScrollText, Users } from "lucide-react";
import { Btn, Card, ErrorNote, LinkBtn, Loading, Stat, inputCls } from "../../components/app/ui";
import { Doodle } from "../../components/landing/Doodle/Doodle";
import { useAuth } from "../../context/AuthContext";
import { paths } from "../../lib/routes";
import { useResource } from "../../lib/useResource";
import { errorMessage } from "../../services/api";
import { downloadResearchExport, getOverview } from "../../services/admin";

function ResearchExport() {
  const [days, setDays] = useState(365);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const download = async () => {
    setBusy(true);
    setErr(null);
    try {
      await downloadResearchExport(days);
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title="Research data">
      <p className="text-sm text-ink-soft">
        A CSV of readings from citizens who turned on research use, and nobody else. It has no names, contact details,
        exact ages, areas or times, and each person gets a code that changes with every download. Each download is
        written to the audit trail.
      </p>
      <div className="mt-4 flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-sm text-ink">
          Readings from the last
          <select value={days} onChange={(e) => setDays(Number(e.target.value))} className={inputCls}>
            <option value={90}>90 days</option>
            <option value={365}>year</option>
            <option value={1825}>5 years</option>
          </select>
        </label>
        <Btn busy={busy} onClick={() => void download()}>
          <Download size={16} aria-hidden="true" /> Download CSV
        </Btn>
      </div>
      {err && <p className="mt-2 text-sm text-danger">{err}</p>}
    </Card>
  );
}

export function AdminDashboard() {
  const { user } = useAuth();
  const res = useResource((s) => getOverview(s), "overview");
  const o = res.data;
  const waiting = o ? o.pending_applications + o.open_concerns : 0;

  return (
    <>
      <section className="relative isolate mb-4 overflow-clip rounded-3xl border border-line bg-surface p-6 md:p-8" aria-labelledby="admin-greeting">
        <Doodle piece="honeycomb" className="-top-10 -right-16 w-56 [--doodle-opacity:0.35]" />
        <Doodle piece="beads" className="right-[22%] -bottom-6 w-28 [--doodle-opacity:0.8]" />
        <p className="text-xs font-semibold uppercase tracking-[0.06em] text-ink-muted">Admin console</p>
        <h1 id="admin-greeting" className="mt-2 text-3xl text-ink md:text-4xl">
          Welcome back, {user?.name.split(" ")[0] ?? "admin"}
        </h1>
        <p className="mt-2 max-w-xl font-display text-xl leading-snug text-ink-soft md:text-2xl">
          {!o
            ? "Loading what needs you today."
            : waiting
              ? `${o.pending_applications} application${o.pending_applications === 1 ? "" : "s"} and ${o.open_concerns} concern${o.open_concerns === 1 ? "" : "s"} are waiting on you.`
              : "Nothing is waiting on you. Every application and concern is handled."}
        </p>
      </section>

      <nav aria-label="Quick actions" className="mb-6 flex flex-wrap gap-2">
        <LinkBtn to={paths.adminApplications}>
          <BadgeCheck size={16} aria-hidden="true" /> Review applications
        </LinkBtn>
        <LinkBtn to={paths.adminConcerns}>
          <LifeBuoy size={16} aria-hidden="true" /> Answer concerns
        </LinkBtn>
        <LinkBtn to={paths.adminAccounts}>
          <Users size={16} aria-hidden="true" /> Accounts
        </LinkBtn>
        <LinkBtn to={paths.adminAudit}>
          <ScrollText size={16} aria-hidden="true" /> Audit trail
        </LinkBtn>
      </nav>
      {res.error && <ErrorNote message={res.error} onRetry={res.reload} />}
      {!o ? (
        !res.error && <Loading />
      ) : (
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat label="Pending applications" value={o.pending_applications} tone={o.pending_applications ? "warn" : undefined} hint={<Link className="text-ink underline underline-offset-4" to={paths.adminApplications}>Review</Link>} />
            <Stat label="Open concerns" value={o.open_concerns} tone={o.open_concerns ? "warn" : undefined} hint={<Link className="text-ink underline underline-offset-4" to={paths.adminConcerns}>Answer</Link>} />
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
          <ResearchExport />
        </div>
      )}
    </>
  );
}
