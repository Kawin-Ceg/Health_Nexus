import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ClipboardList, Clock, MapPin } from "lucide-react";
import { BasisTag } from "../../components/app/ModelInsights";
import { workerState } from "../../components/app/phc";
import { Btn, Empty, Loading, PageHeader, SearchInput, SeverityBadge, cx, inputCls, Status, type StatusTone } from "../../components/app/ui";
import { Detail, Modal, StatePill } from "../../components/app/visits";
import { fmtSpan, fmtStamp } from "../../lib/format";
import { oneOf, useQueryState } from "../../lib/params";
import { citizenRecordPath } from "../../lib/routes";
import type { Severity } from "../../lib/severity";
import { useResource } from "../../lib/useResource";
import { getFeed, getWorklist, markSeen, resolveCitizen, type FeedItem, type WorkItem } from "../../services/phc";
import { CompactList, CompactRow, FlagActions, ResolutionPill, shortSignal } from "../../components/app/compact";
import { VisitForm } from "./Schedule";

const SEVERITIES: Severity[] = ["critical", "high", "moderate", "low"];
const PERIODS = [
  { days: 0, label: "Any time" },
  { days: 1, label: "Last 24 hours" },
  { days: 7, label: "Last 7 days" },
  { days: 30, label: "Last 30 days" },
  { days: 90, label: "Last 3 months" },
];
const FEED_STATUS: Record<FeedItem["status"], { label: string; tone: StatusTone }> = {
  open: { label: "Open", tone: "warn" },
  reviewed: { label: "Resolved", tone: "success" },
  dismissed: { label: "Dismissed", tone: "danger" },
};

function Card({ name, refId, area, when, top, onOpen }: { name: string; refId: string; area: string | null; when: string; top: React.ReactNode; onOpen: () => void }) {
  return (
    <li>
      <button
        type="button"
        onClick={onOpen}
        className="flex h-full w-full flex-col gap-3 rounded-lg border border-line bg-surface p-5 text-left text-sm transition-colors hover:border-ink/40 focus-visible:outline-2 focus-visible:outline-ink"
      >
        <span className="flex items-start justify-between gap-3">
          <span className="min-w-0">
            <span className="block text-base font-semibold leading-snug text-ink">{name}</span>
            <span className="block font-mono text-xs text-ink-muted">{refId}</span>
          </span>
          <span className="flex shrink-0 flex-col items-end gap-1">{top}</span>
        </span>
        <span className="mt-auto flex flex-col gap-1 text-ink-soft">
          <span className="flex items-center gap-1.5"><MapPin size={14} aria-hidden="true" /> {area ?? "Locality not given"}</span>
          <span className="flex items-center gap-1.5"><Clock size={14} aria-hidden="true" /> {when}</span>
        </span>
      </button>
    </li>
  );
}

export function PhcAlerts() {
  const { params, set } = useQueryState();
  const view = oneOf(params.get("view"), ["open", "recent"] as const, "open");
  const [search, setSearch] = useState("");
  const [severity, setSeverity] = useState<Severity | "">("");
  const [locality, setLocality] = useState("");
  const [days, setDays] = useState(0);
  const [openWork, setOpenWork] = useState<string | null>(null);
  const [openFeed, setOpenFeed] = useState<FeedItem | null>(null);

  const work = useResource((s) => getWorklist({}, s), "worklist-all");
  const feed = useResource((s) => (view === "recent" ? getFeed(s, 90) : Promise.resolve(null)), `feed:${view}`);

  const q = search.trim().toLowerCase();
  const since = days ? Date.now() - days * 86400_000 : 0;
  const match = (name: string, ref: string, area: string | null, sev: Severity, at: string) =>
    (!q || `${name} ${ref}`.toLowerCase().includes(q)) &&
    (!severity || sev === severity) &&
    (!locality || area === locality) &&
    new Date(at).getTime() >= since;

  const workRows = useMemo(
    () => (work.data?.items ?? []).filter((w) => match(w.citizen.name, w.citizen.ref, w.citizen.area, w.worst_severity, w.last_flagged_at)),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [work.data, q, severity, locality, since],
  );
  const feedRows = useMemo(
    () => (feed.data?.items ?? []).filter((f) => match(f.citizen.name, f.citizen.ref, f.citizen.area, f.severity, f.measured_at)),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [feed.data, q, severity, locality, since],
  );
  const localities = useMemo(() => {
    const all = [...(work.data?.items ?? []).map((w) => w.citizen.area), ...(feed.data?.items ?? []).map((f) => f.citizen.area)];
    return [...new Set(all.filter((a): a is string => !!a))].sort();
  }, [work.data, feed.data]);
  const current = work.data?.items.find((w) => w.citizen.id === openWork) ?? null;

  const blocked = workerState(work);
  if (blocked) return blocked;

  return (
    <>
      <PageHeader title="Alerts" lead="Flagged readings in your catchment, one card per citizen. Open a card to resolve, dismiss or book a visit." />
      <div role="tablist" aria-label="View" className="mb-4 inline-flex rounded-full border border-line bg-surface p-1">
        {(
          [
            ["open", "Needs review", work.data?.total_citizens],
            ["recent", "Recent activity", feed.data?.items.length],
          ] as const
        ).map(([id, label, n]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={view === id}
            onClick={() => set({ view: id === "open" ? null : id })}
            className={cx("min-h-10 rounded-full px-5 text-sm font-semibold transition-colors", view === id ? "bg-ink text-paper" : "text-ink-soft hover:text-ink")}
          >
            {label} {n != null && <span className="tabular-nums opacity-70">{n}</span>}
          </button>
        ))}
      </div>

      <div className="mb-5 grid gap-3 lg:grid-cols-[2fr_3fr]">
        <SearchInput value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search name or HN- reference" aria-label="Search" />
        <div className="grid grid-cols-3 gap-3">
          <select aria-label="When" value={days} onChange={(e) => setDays(Number(e.target.value))} className={cx(inputCls, "px-3")}>
            {PERIODS.map((p) => (
              <option key={p.days} value={p.days}>{p.label}</option>
            ))}
          </select>
          <select aria-label="Severity" value={severity} onChange={(e) => setSeverity(e.target.value as Severity | "")} className={cx(inputCls, "px-3")}>
            <option value="">All severities</option>
            {SEVERITIES.map((s) => (
              <option key={s} value={s} className="capitalize">{s[0].toUpperCase() + s.slice(1)}</option>
            ))}
          </select>
          <select aria-label="Locality" value={locality} onChange={(e) => setLocality(e.target.value)} className={cx(inputCls, "px-3")}>
            <option value="">All localities</option>
            {localities.map((l) => (
              <option key={l} value={l}>{l}</option>
            ))}
          </select>
        </div>
      </div>

      {view === "open" ? (
        !work.data ? (
          <Loading />
        ) : workRows.length === 0 ? (
          <Empty title="Nobody needs review">{work.data.items.length ? "No flagged citizen matches these filters." : "Every flag in your catchment has been handled."}</Empty>
        ) : (
          <ul className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {workRows.map((w) => (
              <Card
                key={w.citizen.id}
                name={w.citizen.name}
                refId={w.citizen.ref}
                area={w.citizen.area}
                when={`Open for ${fmtSpan(w.first_flagged_at)}`}
                onOpen={() => setOpenWork(w.citizen.id)}
                top={
                  <>
                    <SeverityBadge severity={w.worst_severity} />
                    {w.next_visit ? (
                      <Status tone="info">Visit booked</Status>
                    ) : (
                      <Status tone="warn">{w.open_flags} open</Status>
                    )}
                  </>
                }
              />
            ))}
          </ul>
        )
      ) : !feed.data ? (
        feed.error ? <p className="text-sm text-danger">{feed.error}</p> : <Loading />
      ) : feedRows.length === 0 ? (
        <Empty title="No flags match" />
      ) : (
        <ul className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {feedRows.map((f) => (
            <Card
              key={f.processed_id}
              name={f.citizen.name}
              refId={f.citizen.ref}
              area={f.citizen.area}
              when={fmtStamp(f.measured_at)}
              onOpen={() => setOpenFeed(f)}
              top={
                <>
                  <SeverityBadge severity={f.severity} />
                  <Status tone={FEED_STATUS[f.status].tone}>{FEED_STATUS[f.status].label}</Status>
                </>
              }
            />
          ))}
        </ul>
      )}

      {current && <WorkDetails item={current} onClose={() => setOpenWork(null)} onChanged={work.reload} />}
      {openFeed && (
        <Modal title={openFeed.citizen.name} onClose={() => setOpenFeed(null)}>
          <div className="flex flex-col gap-5">
            <div className="flex flex-wrap gap-2">
              <SeverityBadge severity={openFeed.severity} />
              <Status tone={FEED_STATUS[openFeed.status].tone}>{FEED_STATUS[openFeed.status].label}</Status>
            </div>
            <dl className="grid gap-4 sm:grid-cols-2">
              <Detail label="Reference">{openFeed.citizen.ref}</Detail>
              <Detail label="Locality">{openFeed.citizen.area ?? "—"}</Detail>
              <Detail label="What was flagged">{openFeed.signal ?? "Reading outside the usual range"}</Detail>
              <Detail label="Reading taken">{fmtStamp(openFeed.measured_at)}</Detail>
              <Detail label="Handled by">{openFeed.reviewed_by ?? (openFeed.status === "open" ? "Not yet" : "—")}</Detail>
              <Detail label="Handled on">{openFeed.reviewed_at ? fmtStamp(openFeed.reviewed_at) : "—"}</Detail>
            </dl>
            <Link to={citizenRecordPath(openFeed.citizen.id)} className="w-fit text-sm font-semibold text-ink underline underline-offset-4">Open full record</Link>
          </div>
        </Modal>
      )}
    </>
  );
}

function WorkDetails({ item, onClose, onChanged }: { item: WorkItem; onClose: () => void; onChanged: () => void }) {
  const [booking, setBooking] = useState(false);
  const [flagId, setFlagId] = useState<string | null>(null);
  const c = item.citizen;
  const flags = [...item.flags].sort((a, b) => b.measured_at.localeCompare(a.measured_at));
  const flag = flags.find((f) => f.processed_id === flagId) ?? null;

  if (booking) {
    return (
      <VisitForm
        preset={c}
        caseId={item.flags[0]?.processed_id}
        onClose={() => setBooking(false)}
        onSaved={() => {
          onChanged();
          onClose();
        }}
      />
    );
  }

  if (flag) {
    return (
      <Modal title={shortSignal(flag.signal)} onClose={() => setFlagId(null)}>
        <div className="flex flex-col gap-5">
          <div className="flex flex-wrap items-center gap-2">
            <SeverityBadge severity={flag.severity} />
            <ResolutionPill status="open" />
            <BasisTag basis={flag.basis} />
          </div>
          <p className="text-base text-ink">{flag.signal ?? "Reading outside the usual range"}</p>
          <dl className="grid gap-4 sm:grid-cols-2">
            <Detail label="Citizen">{c.name} · {c.ref}</Detail>
            <Detail label="Reading taken">{fmtStamp(flag.measured_at)}</Detail>
            <Detail label="Symptoms">{flag.symptoms.length ? flag.symptoms.join(", ") : "None reported"}</Detail>
          </dl>
          <FlagActions
            onResolve={async (body) => {
              await markSeen(flag.processed_id, body);
              setFlagId(null);
              onChanged();
            }}
            extra={<Btn tone="ghost" onClick={() => setFlagId(null)}>Back to all flags</Btn>}
          />
        </div>
      </Modal>
    );
  }

  return (
    <Modal title={c.name} onClose={onClose} wide>
      <div className="flex flex-col gap-5">
        <div className="flex flex-wrap items-center gap-2">
          <SeverityBadge severity={item.worst_severity} />
          <Status tone="warn">
            {item.open_flags} open flag{item.open_flags === 1 ? "" : "s"}
          </Status>
          {item.next_visit && <StatePill visit={item.next_visit} />}
        </div>
        <dl className="grid gap-4 sm:grid-cols-3">
          <Detail label="Reference">{c.ref}</Detail>
          <Detail label="Locality">{c.area ?? "—"}</Detail>
          <Detail label="Phone">{c.phone ? <a href={`tel:${c.phone.replace(/[^\d+]/g, "")}`} className="underline underline-offset-4">{c.phone}</a> : "—"}</Detail>
          <Detail label="Open for">{fmtSpan(item.first_flagged_at)}</Detail>
          {item.next_visit && <Detail label="Visit booked">{fmtStamp(item.next_visit.scheduled_for)}</Detail>}
        </dl>
        <div>
          <h3 className="mb-1 text-base font-bold text-ink">Flags, newest first</h3>
          <p className="mb-2 text-xs text-ink-muted">Open a flag to resolve or dismiss just that one.</p>
          <CompactList className="rounded-xl border border-line">
            {flags.map((f) => (
              <CompactRow key={f.processed_id} topic={shortSignal(f.signal)} at={f.measured_at} right={<SeverityBadge severity={f.severity} />} onOpen={() => setFlagId(f.processed_id)} />
            ))}
          </CompactList>
          {item.open_flags > item.flags_shown && <p className="mt-1 text-xs text-ink-muted">Showing the worst {item.flags_shown} of {item.open_flags}.</p>}
        </div>
        <FlagActions
          resolveLabel={item.open_flags > 1 ? `Resolve all ${item.open_flags}` : "Resolve"}
          onResolve={async (body) => {
            await resolveCitizen(c.id, body);
            onChanged();
            onClose();
          }}
          extra={
            <>
              {!item.next_visit && <Btn tone="info" onClick={() => setBooking(true)}>Book visit</Btn>}
              <Link to={citizenRecordPath(c.id)} className="inline-flex min-h-11 items-center gap-2 rounded-full border border-line px-5 font-semibold text-ink hover:bg-paper">
                <ClipboardList size={16} aria-hidden="true" /> Full record
              </Link>
            </>
          }
        />
      </div>
    </Modal>
  );
}
