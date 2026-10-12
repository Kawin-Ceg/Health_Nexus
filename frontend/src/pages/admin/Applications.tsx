import { useToast } from "../../components/app/Toaster";
import { useState } from "react";
import { Btn, Card, Empty, ErrorNote, Labelled, Loading, PageHeader, Tabs, cx, inputCls } from "../../components/app/ui";
import { fmtAgo, fmtDateTime } from "../../lib/format";
import { useDebounced } from "../../lib/useDebounced";
import { useResource } from "../../lib/useResource";
import { errorMessage } from "../../services/api";
import { DESIGNATIONS } from "../../services/auth";
import {
  approveApplication,
  getApplication,
  getApplications,
  rejectApplication,
  revokeApplication,
  searchFacilities,
  type ApplicationDetail,
  type ApplicationStatus,
  type FacilityOption,
} from "../../services/admin";

const STATUS_LABEL: Record<ApplicationStatus, string> = { pending: "Pending", approved: "Approved", rejected: "Rejected" };
const STATUS_CLS: Record<ApplicationStatus, string> = {
  pending: "bg-warn/15 text-warn",
  approved: "bg-success-soft text-success",
  rejected: "bg-danger-soft text-danger",
};
const designation = (d: string) => DESIGNATIONS.find((x) => x.value === d)?.label ?? d;

export function Applications() {
  const [status, setStatus] = useState<ApplicationStatus | "">("pending");
  const [search, setSearch] = useState("");
  const q = useDebounced(search);
  const [selected, setSelected] = useState<string | null>(null);

  const query = { status, q };
  const list = useResource((s) => getApplications(query, s), JSON.stringify(query));
  const d = list.data;

  return (
    <>
      <PageHeader title="PHC worker applications" lead="Check each applicant against the health-centre registry, then approve, reject, or revoke access." />
      {d && (
        <Tabs
          label="Status"
          value={status || "all"}
          onChange={(v) => setStatus(v === "all" ? "" : v)}
          tabs={[
            { id: "pending" as const, label: `Pending (${d.counts.pending})` },
            { id: "approved" as const, label: `Approved (${d.counts.approved})` },
            { id: "rejected" as const, label: `Rejected (${d.counts.rejected})` },
            { id: "all" as const, label: "All" },
          ]}
        />
      )}
      <input type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search name, email, centre or employee ID" aria-label="Search" className={cx(inputCls, "mb-4 max-w-md")} />
      {list.error && <ErrorNote message={list.error} onRetry={list.reload} />}
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
        <div>
          {!d ? (
            !list.error && <Loading />
          ) : d.items.length === 0 ? (
            <Empty title="No applications here" />
          ) : (
            <ul className={cx("flex flex-col gap-2", list.loading && "opacity-60")}>
              {d.items.map((a) => (
                <li key={a.id}>
                  <button
                    type="button"
                    onClick={() => setSelected(a.id)}
                    className={cx(
                      "w-full rounded-2xl border bg-surface p-4 text-left hover:border-brand",
                      selected === a.id ? "border-brand" : "border-line",
                    )}
                  >
                    <span className="flex items-center justify-between gap-2">
                      <span className="font-semibold text-ink">{a.applicant.name}</span>
                      <span className={cx("rounded-full px-2 py-0.5 text-xs font-semibold", STATUS_CLS[a.status])}>{STATUS_LABEL[a.status]}</span>
                    </span>
                    <span className="mt-1 block text-sm text-ink-soft">
                      {designation(a.designation)} · {a.phc_name}, {a.district}
                    </span>
                    <span className="mt-1 block text-xs text-ink-soft">
                      Applied {fmtAgo(a.created_at)}
                      {!a.applicant.is_verified && " · email not confirmed"}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          {selected ? (
            <Review key={selected} id={selected} onChanged={list.reload} />
          ) : (
            <Empty title="Pick an application">Its details, the registry match and the decision buttons appear here.</Empty>
          )}
        </div>
      </div>
    </>
  );
}

/** Mounted with key={id}, so switching applications starts from fresh state. */
function Review({ id, onChanged }: { id: string; onChanged: () => void }) {
  const res = useResource((s) => getApplication(id, s), id);
  // The server's answer to a decision replaces the loaded copy.
  const [decided, setDecided] = useState<ApplicationDetail | null>(null);
  const a = decided ?? res.data;

  const [picked, setPicked] = useState<FacilityOption | null>(null);
  const facility = picked ?? a?.facility ?? a?.suggested_facility ?? null;
  const [reason, setReason] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<"approve" | "reject" | "revoke" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { notify } = useToast();

  if (res.error) return <ErrorNote message={res.error} onRetry={res.reload} />;
  if (!a) return <Loading />;

  const act = async (kind: "approve" | "reject" | "revoke", call: () => Promise<ApplicationDetail>) => {
    setBusy(kind);
    setError(null);
    try {
      const next = await call();
      setDecided(next);
      notify({ tone: "success", title: { approve: "Application approved", reject: "Application rejected", revoke: "Access revoked" }[kind], body: next.applicant.name });
      setReason("");
      onChanged();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(null);
    }
  };
  const approve = () => facility && act("approve", () => approveApplication(a.id, facility.id, note));
  const decline = () =>
    a.status === "approved"
      ? act("revoke", () => revokeApplication(a.id, reason))
      : act("reject", () => rejectApplication(a.id, reason));

  return (
    <Card title={a.applicant.name} aside={<span className={cx("rounded-full px-2 py-0.5 text-xs font-semibold", STATUS_CLS[a.status])}>{STATUS_LABEL[a.status]}</span>}>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
        <Row label="Email" value={`${a.applicant.email}${a.applicant.is_verified ? "" : " (not confirmed)"}`} />
        <Row label="Employee ID" value={a.employee_id} />
        <Row label="Designation" value={designation(a.designation)} />
        <Row label="Years of service" value={String(a.years_of_service)} />
        <Row label="Claimed centre" value={a.phc_name} />
        <Row label="District, state" value={`${a.district}, ${a.state}`} />
        {a.facility && <Row label="Linked centre" value={`${a.facility.name} (${a.facility.facility_code})`} />}
        {a.rejection_reason && <Row label="Reason given" value={a.rejection_reason} />}
        {a.reviewed_at && <Row label="Last decision" value={`${a.reviewed_by ?? "Unknown"}, ${fmtDateTime(a.reviewed_at)}`} />}
      </dl>

      {a.status !== "approved" && (
        <div className="mt-5 flex flex-col gap-3 border-t border-line pt-4">
          <h3 className="text-sm font-semibold text-ink">Approve</h3>
          {a.suggested_facility ? (
            <p className="text-xs text-ink-soft">The registry has exactly one match for the claimed centre: {a.suggested_facility.name}.</p>
          ) : (
            <p className="text-xs text-warn">No single registry match for "{a.phc_name}". Pick the centre by hand.</p>
          )}
          <FacilityPicker value={facility} onChange={setPicked} district={a.district} />
          <Labelled label="Note (optional)">
            <input className={inputCls} value={note} maxLength={500} onChange={(e) => setNote(e.target.value)} />
          </Labelled>
          <Btn tone="primary" busy={busy === "approve"} disabled={!facility || !a.applicant.is_verified || !!busy} onClick={approve}>
            Approve and link to {facility?.name ?? "a centre"}
          </Btn>
          {!a.applicant.is_verified && <p className="text-xs text-ink-soft">The applicant must confirm their email before approval.</p>}
        </div>
      )}

      {a.status !== "rejected" && (
        <div className="mt-5 flex flex-col gap-3 border-t border-line pt-4">
          <h3 className="text-sm font-semibold text-ink">{a.status === "approved" ? "Revoke access" : "Reject"}</h3>
          <Labelled label="Reason" hint="Shown to the applicant and kept in the audit trail.">
            <input className={inputCls} value={reason} maxLength={500} onChange={(e) => setReason(e.target.value)} />
          </Labelled>
          <Btn
            tone="danger"
            busy={busy === "reject" || busy === "revoke"}
            disabled={reason.trim().length < 3 || !!busy}
            onClick={decline}
          >
            {a.status === "approved" ? "Revoke worker access" : "Reject application"}
          </Btn>
          {a.status === "approved" && <p className="text-xs text-ink-soft">Their booked visits are cancelled and the citizens are told.</p>}
        </div>
      )}
      {error && <div className="mt-3"><ErrorNote message={error} /></div>}

      {a.history.length > 0 && (
        <div className="mt-5 border-t border-line pt-4">
          <h3 className="mb-2 text-sm font-semibold text-ink">History</h3>
          <ol className="flex flex-col gap-2 text-sm">
            {a.history.map((h, i) => (
              <li key={i} className="text-ink-soft">
                <span className="text-ink">{h.action.replace("application_", "").replace("_", " ")}</span> by {h.actor ?? "system"}, {fmtDateTime(h.created_at)}
                {h.reason && <span className="block text-xs">"{h.reason}"</span>}
              </li>
            ))}
          </ol>
        </div>
      )}
    </Card>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-ink-soft">{label}</dt>
      <dd className="break-words text-ink">{value}</dd>
    </div>
  );
}

function FacilityPicker({ value, onChange, district }: { value: FacilityOption | null; onChange: (f: FacilityOption) => void; district: string }) {
  const [q, setQ] = useState("");
  const term = useDebounced(q);
  const res = useResource((s) => searchFacilities({ q: term, district: term ? undefined : district }, s), `${term}|${district}`);

  return (
    <div className="flex flex-col gap-2">
      <Labelled label="Health centre" hint={term ? "Searching every district." : `Showing centres in ${district}. Type to search everywhere.`}>
        <input type="search" className={inputCls} value={q} onChange={(e) => setQ(e.target.value)} placeholder="Name or facility code" />
      </Labelled>
      <ul className="max-h-48 overflow-y-auto rounded-2xl border border-line">
        {res.data?.length === 0 && <li className="px-3 py-2 text-sm text-ink-soft">No centres found.</li>}
        {res.data?.map((f) => (
          <li key={f.id}>
            <button
              type="button"
              onClick={() => onChange(f)}
              className={cx("w-full px-3 py-2 text-left text-sm hover:bg-paper-raised", value?.id === f.id && "bg-brand-soft text-brand")}
            >
              {f.name} <span className="text-xs text-ink-soft">· {f.district}, {f.state} · {f.facility_code}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
