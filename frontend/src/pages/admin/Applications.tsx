import { useToast } from "../../components/app/Toaster";
import { useEffect, useState, type ReactNode } from "react";
import { BadgeCheck, Clock, MailCheck, Building2, IdCard, Mail, X } from "lucide-react";
import { Empty, ErrorNote, Labelled, Loading, PageHeader, SearchInput, cx, inputCls, Status, type StatusTone } from "../../components/app/ui";
import { fmtAgo, fmtDateTime } from "../../lib/format";
import { useDebounced } from "../../lib/useDebounced";
import { useResource } from "../../lib/useResource";
import { errorMessage } from "../../services/api";
import { ReviewDocuments } from "../../components/app/VerificationDocuments";
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

const designation = (d: string) => DESIGNATIONS.find((x) => x.value === d)?.label ?? d;

const FILTERS: { id: ApplicationStatus; label: string; dot: string }[] = [
  { id: "pending", label: "Pending", dot: "bg-amber-400" },
  { id: "approved", label: "Approved", dot: "bg-green-500" },
  { id: "rejected", label: "Rejected", dot: "bg-red-500" },
];

export function Applications() {
  const [status, setStatus] = useState<ApplicationStatus>("pending");
  const [search, setSearch] = useState("");
  const q = useDebounced(search);
  const [selected, setSelected] = useState<string | null>(() => new URLSearchParams(window.location.search).get("open"));
  const [district, setDistrict] = useState("");
  const [role, setRole] = useState("");
  const [days, setDays] = useState<number | "">("");

  const query = { status, q, district, designation: role, days };
  const list = useResource((s) => getApplications(query, s), JSON.stringify(query));
  const d = list.data;

  return (
    <div className="font-sans">
      <PageHeader title="PHC worker applications" />
      <SearchInput
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Search name, email, centre or employee ID"
        aria-label="Search applications"
        className="mb-4"
      />
      <div role="tablist" aria-label="Status" className="mb-5 flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            type="button"
            role="tab"
            aria-selected={status === f.id}
            onClick={() => setStatus(f.id)}
            className={cx(
              "inline-flex min-h-10 items-center gap-2 rounded-full border px-4 text-sm font-medium",
              status === f.id ? "border-ink bg-ink text-paper" : "border-line bg-surface text-ink hover:border-ink/40",
            )}
          >
            {f.label}
            {d && <span className="tabular-nums opacity-70">{d.counts[f.id]}</span>}
          </button>
        ))}
      </div>
      <div className="mb-5 flex flex-wrap gap-3">
        <select aria-label="District" value={district} onChange={(e) => setDistrict(e.target.value)} className={cx(inputCls, "w-auto!")}>
          <option value="">All districts</option>
          {d?.districts.map((x) => (
            <option key={x} value={x}>{x}</option>
          ))}
        </select>
        <select aria-label="Role" value={role} onChange={(e) => setRole(e.target.value)} className={cx(inputCls, "w-auto!")}>
          <option value="">All roles</option>
          {DESIGNATIONS.map((x) => (
            <option key={x.value} value={x.value}>{x.label}</option>
          ))}
        </select>
        <select aria-label="Applied" value={days} onChange={(e) => setDays(e.target.value ? Number(e.target.value) : "")} className={cx(inputCls, "w-auto!")}>
          <option value="">Any time</option>
          <option value={1}>Last 24 hours</option>
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
        </select>
        {(district || role || days) && (
          <button type="button" onClick={() => { setDistrict(""); setRole(""); setDays(""); }} className="text-sm text-ink-soft underline underline-offset-4">
            Clear filters
          </button>
        )}
      </div>
      {list.error && <ErrorNote message={list.error} onRetry={list.reload} />}
      {!d ? (
        !list.error && <Loading />
      ) : d.items.length === 0 ? (
        <Empty title="No applications here" />
      ) : (
        <ul className={cx("grid gap-5 md:grid-cols-2 2xl:grid-cols-3", list.loading && "opacity-60")}>
          {d.items.map((a) => (
            <li key={a.id}>
              <button
                type="button"
                onClick={() => setSelected(a.id)}
                className="flex h-full w-full flex-col gap-5 rounded-lg border border-line bg-surface p-5 text-left text-sm transition-colors hover:border-ink/40 focus-visible:outline-2 focus-visible:outline-ink"
              >
                <span className="flex items-start gap-4">
                  <Avatar name={a.applicant.name} size="sm" />
                  <span className="min-w-0 flex-1">
                    <span className="block text-base font-semibold leading-snug text-ink">{a.applicant.name}</span>
                    <span className="mt-0.5 block break-words text-ink-muted">{a.applicant.email}</span>
                  </span>
                  <span className="shrink-0 rounded-md border border-line px-2.5 py-1 text-xs font-semibold text-ink">
                    {a.designation === "asha_supervisor" ? "ASHA" : "PHC"}
                  </span>
                </span>
                <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2">
                  <dt className="text-ink-muted">Role</dt>
                  <dd className="text-ink">{designation(a.designation)}</dd>
                  <dt className="text-ink-muted">PHC</dt>
                  <dd className="break-words text-ink">{a.phc_name}</dd>
                  <dt className="text-ink-muted">District</dt>
                  <dd className="text-ink">{a.district}</dd>
                </dl>
                <span className="mt-auto flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
                  <span>
                    <span className="block text-xs text-ink-muted">Applied</span>
                    <span className="text-ink">{fmtAgo(a.created_at)}</span>
                  </span>
                  <span className="text-right">
                    <span className="block text-xs text-ink-muted">Status</span>
                    <Status tone={PILL[a.status].tone}>
                      {FILTERS.find((f) => f.id === a.status)!.label}
                    </Status>
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {selected && (
        <Modal onClose={() => setSelected(null)}>
          <Review key={selected} id={selected} onChanged={list.reload} />
        </Modal>
      )}
    </div>
  );
}

function Avatar({ name, size }: { name: string; size: "sm" | "lg" }) {
  const initials = name.split(/\s+/).map((p) => p[0]).slice(0, 2).join("").toUpperCase();
  return (
    <span
      className={cx(
        "grid shrink-0 place-items-center bg-paper-raised text-ink-muted",
        size === "lg" ? "h-28 w-24 rounded-xl border-2 border-dashed border-line-strong/40 text-3xl" : "h-11 w-11 rounded-full text-sm font-semibold",
      )}
      aria-hidden="true"
    >
      {size === "lg" ? (
        <svg viewBox="0 0 64 80" className="h-20 w-16 fill-current opacity-60">
          <circle cx="32" cy="26" r="14" />
          <path d="M6 78c0-15 12-26 26-26s26 11 26 26z" />
        </svg>
      ) : (
        initials
      )}
    </span>
  );
}

function Modal({ children, onClose }: { children: ReactNode; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = overflow;
    };
  }, [onClose]);
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-3 backdrop-blur-sm" onClick={onClose}>
      <div role="dialog" aria-modal="true" className="relative w-full max-w-5xl" onClick={(e) => e.stopPropagation()}>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="absolute top-3 right-3 z-10 grid h-9 w-9 place-items-center rounded-full bg-paper text-ink hover:bg-paper-raised"
        >
          <X size={18} aria-hidden="true" />
        </button>
        {children}
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="px-5 py-4">
      <h3 className="mb-4 font-sans text-base font-bold text-ink">{title}</h3>
      {children}
    </section>
  );
}

function Review({ id, onChanged }: { id: string; onChanged: () => void }) {
  const res = useResource((s) => getApplication(id, s), id);
  const [decided, setDecided] = useState<ApplicationDetail | null>(null);
  const a = decided ?? res.data;

  const [picked, setPicked] = useState<FacilityOption | null>(null);
  const [choosing, setChoosing] = useState(false);
  const facility = picked ?? a?.facility ?? a?.suggested_facility ?? null;
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<"approve" | "reject" | "revoke" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { notify } = useToast();

  if (res.error) return <div className="rounded-3xl bg-surface p-6"><ErrorNote message={res.error} onRetry={res.reload} /></div>;
  if (!a) return <div className="rounded-3xl bg-surface p-6"><Loading /></div>;

  const act = async (kind: "approve" | "reject" | "revoke", call: () => Promise<ApplicationDetail>) => {
    setBusy(kind);
    setError(null);
    try {
      const next = await call();
      setDecided(next);
      notify({ tone: "success", title: { approve: "Application approved", reject: "Application rejected", revoke: "Access revoked" }[kind], body: next.applicant.name });
      setNote("");
      onChanged();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(null);
    }
  };
  const approve = () => facility && act("approve", () => approveApplication(a.id, facility.id, note));
  const decline = () =>
    a.status === "approved" ? act("revoke", () => revokeApplication(a.id, note)) : act("reject", () => rejectApplication(a.id, note));

  return (
    <article className="flex max-h-[calc(100dvh-1.5rem)] flex-col overflow-hidden rounded-2xl border border-line bg-surface font-sans text-sm shadow-xl">
      <div className="grid shrink-0 gap-5 p-5 md:grid-cols-[160px_1fr] md:gap-6">
        <div className="flex flex-col items-center gap-2 text-center md:items-start md:border-r md:border-line md:pr-6 md:text-left">
          <Avatar name={a.applicant.name} size="lg" />
          <div>
            <p className="text-lg font-bold leading-snug text-ink">{a.applicant.name}</p>
            <p className="text-sm text-ink-soft">{designation(a.designation)}</p>
          </div>
          <StatusPill status={a.status} />
        </div>
        <dl className="grid content-center gap-x-6 gap-y-5 sm:grid-cols-2 lg:grid-cols-3">
          <Row icon={Mail} label="Email" value={a.applicant.email} />
          <Row icon={IdCard} label="Employee ID" value={a.employee_id} />
          <Row icon={Building2} label="Claimed PHC" value={a.phc_name} />
          <Row icon={MailCheck} label="Email verification" value={a.applicant.is_verified ? "Confirmed" : "Not confirmed yet"} />
          <Row
            icon={BadgeCheck}
            label="Registry match"
            value={a.suggested_facility ? `${a.suggested_facility.name} (${a.suggested_facility.facility_code})` : "Not found in the registry"}
          />
          <Row icon={Clock} label="Applied on" value={fmtDateTime(a.created_at)} />
        </dl>
      </div>

      <div className="grid min-h-0 flex-1 border-t border-line md:grid-cols-2">
        <div className="min-h-0 overflow-y-auto md:border-r md:border-line">
      <Section title="Documents">
        <ReviewDocuments key={a.id} applicationId={a.id} docs={a.documents} />
      </Section>

      </div>
        <div className="min-h-0 overflow-y-auto">
      <Section title="Decision">
        <div className="flex flex-col gap-4">
          {a.status !== "approved" &&
            (facility && !choosing ? (
              <p className="flex flex-wrap items-center gap-2 text-ink">
                Approving links them to <span className="font-semibold">{facility.name}</span>
                <span className="text-ink-muted">· {facility.facility_code}</span>
                <button type="button" onClick={() => setChoosing(true)} className="text-xs text-ink-soft underline underline-offset-4">
                  Wrong centre?
                </button>
              </p>
            ) : (
              <>
                {!a.suggested_facility && <p className="text-warn">"{a.phc_name}" is not in the registry. Pick the centre it refers to.</p>}
                <FacilityPicker value={facility} onChange={(f) => { setPicked(f); setChoosing(false); }} district={a.district} />
              </>
            ))}
          <Labelled
            label="Note"
            hint={
              a.status === "approved"
                ? "Required to revoke. Shown to the worker and kept in the audit trail."
                : "Goes with your decision: optional when approving, required when rejecting. Kept in the audit trail."
            }
          >
            <textarea rows={2} className={cx(inputCls, "py-2")} value={note} maxLength={500} onChange={(e) => setNote(e.target.value)} />
          </Labelled>
          <div className="flex flex-wrap gap-3">
            {a.status !== "approved" && (
              <button
                type="button"
                onClick={approve}
                disabled={!facility || !a.applicant.is_verified || !!busy}
                className="inline-flex min-h-11 items-center rounded-full bg-green-600 text-white hover:bg-green-700 px-5 font-semibold disabled:opacity-50"
              >
                {busy === "approve" ? "Approving…" : "Approve"}
              </button>
            )}
            {a.status !== "rejected" && (
              <button
                type="button"
                onClick={decline}
                disabled={note.trim().length < 3 || !!busy}
                className="inline-flex min-h-11 items-center rounded-full bg-red-600 text-white hover:bg-red-700 px-5 font-semibold disabled:opacity-50"
              >
                {busy === "reject" || busy === "revoke" ? "Saving…" : a.status === "approved" ? "Revoke access" : "Reject"}
              </button>
            )}
          </div>
          {!a.applicant.is_verified && a.status !== "approved" && <p className="text-ink-soft">The applicant must confirm their email before approval.</p>}
          {a.status === "approved" && <p className="text-ink-soft">Revoking cancels their booked visits and tells the citizens.</p>}
          {a.rejection_reason && <p className="text-ink-soft">Reason given last time: "{a.rejection_reason}"</p>}
        </div>
      </Section>
        </div>
      </div>
      {error && <div className="px-6 pb-4"><ErrorNote message={error} /></div>}

    </article>
  );
}

function Row({ icon: Icon, label, value }: { icon: typeof Mail; label: string; value: string }) {
  return (
    <div className="flex min-w-0 gap-3">
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-line text-ink-soft">
        <Icon size={18} aria-hidden="true" />
      </span>
      <div className="min-w-0">
        <dt className="text-sm font-semibold text-ink">{label}</dt>
        <dd className="mt-0.5 break-words text-sm text-ink-soft">{value}</dd>
      </div>
    </div>
  );
}

const PILL: Record<ApplicationStatus, { label: string; tone: StatusTone }> = {
  pending: { label: "Pending review", tone: "warn" },
  approved: { label: "Approved", tone: "success" },
  rejected: { label: "Rejected", tone: "danger" },
};

function StatusPill({ status }: { status: ApplicationStatus }) {
  return (
    <Status tone={PILL[status].tone}>
      {PILL[status].label}
    </Status>
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
