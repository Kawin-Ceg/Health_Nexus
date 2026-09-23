import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { BookVisitForm, PersonLine, ResolveControls, workerState } from "../../components/app/phc";
import { Btn, Card, Empty, Loading, PageHeader, SeverityBadge, Tabs, VisitBadge, cx, inputCls } from "../../components/app/ui";
import { fmtAgo, fmtDateTime, fmtVisit, plural } from "../../lib/format";
import { oneOf, textParam, useQueryState } from "../../lib/params";
import { citizenRecordPath } from "../../lib/routes";
import { useResource } from "../../lib/useResource";
import { getFeed, getWorklist, resolveCitizen, type WorkItem } from "../../services/phc";

/** A search box that only updates the URL after typing pauses. */
function useDebounced(value: string, ms = 300) {
  const [out, setOut] = useState(value);
  useEffect(() => {
    const t = window.setTimeout(() => setOut(value), ms);
    return () => window.clearTimeout(t);
  }, [value, ms]);
  return out;
}

function Citizen({ item, onChanged }: { item: WorkItem; onChanged: () => void }) {
  const [booking, setBooking] = useState(false);
  return (
    <li className="rounded-2xl border border-line bg-surface p-4">
      <div className="flex flex-wrap items-start gap-4">
        <SeverityBadge severity={item.worst_severity} className="mt-0.5" />
        <div className="min-w-56 flex-1">
          <PersonLine person={item.citizen} />
          <p className="mt-1 text-sm text-ink">{item.worst_signal ?? "Reading outside the usual range"}</p>
          <p className="text-xs text-ink-soft">
            {plural(item.open_flags, "open flag")} · first {fmtAgo(item.first_flagged_at)}, latest {fmtAgo(item.last_flagged_at)}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <ResolveControls
            reviewLabel="Resolve all"
            onResolve={async (body) => {
              await resolveCitizen(item.citizen.id, body);
              onChanged();
            }}
          />
          {!item.next_visit && <Btn onClick={() => setBooking((b) => !b)}>Book visit</Btn>}
          <Link to={citizenRecordPath(item.citizen.id)} className="inline-flex min-h-10 items-center rounded-xl px-3 text-sm font-semibold text-brand">
            Record
          </Link>
        </div>
      </div>
      {item.next_visit && (
        <p className="mt-3 flex flex-wrap items-center gap-2 text-sm text-ink-soft">
          Visit {fmtVisit(item.next_visit.scheduled_for)} <VisitBadge state={item.next_visit.state} />
        </p>
      )}
      {item.flags.length > 1 && (
        <details className="mt-3 text-sm">
          <summary className="cursor-pointer text-ink-soft">
            All open flags{item.open_flags > item.flags_shown ? ` (worst ${item.flags_shown} of ${item.open_flags})` : ""}
          </summary>
          <ul className="mt-2 flex flex-col gap-1">
            {item.flags.map((f) => (
              <li key={f.processed_id} className="flex flex-wrap items-center gap-2">
                <SeverityBadge severity={f.severity} />
                <span className="text-ink">{f.signal}</span>
                <span className="text-xs text-ink-soft">{fmtDateTime(f.measured_at)}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
      {booking && (
        <BookVisitForm
          citizen={item.citizen}
          caseId={item.flags[0]?.processed_id}
          onCancel={() => setBooking(false)}
          onBooked={() => {
            setBooking(false);
            onChanged();
          }}
        />
      )}
    </li>
  );
}

export function PhcAlerts() {
  const { params, set } = useQueryState();
  const view = oneOf(params.get("view"), ["open", "recent"] as const, "open");
  const locality = textParam(params.get("locality"), 120);
  const [search, setSearch] = useState(() => textParam(params.get("q"), 80));
  const q = useDebounced(search);
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    set({ q });
  }, [q, set]);

  const work = useResource((s) => getWorklist({ q, locality }, s), `work:${q}:${locality}`);
  const feed = useResource(
    (s) => (view === "recent" ? getFeed(s) : Promise.resolve(null)),
    `feed:${view}`,
  );

  const blocked = workerState(work);
  if (blocked) return blocked;

  return (
    <>
      <PageHeader title="Alerts" lead="Flags grouped by person: one citizen is one piece of work. Worst first." />
      <Tabs
        label="View"
        value={view}
        onChange={(v) => set({ view: v === "open" ? null : v })}
        tabs={[
          { id: "open", label: work.data ? `Needs review (${work.data.total_citizens})` : "Needs review" },
          { id: "recent", label: "Recent activity" },
        ]}
      />

      {view === "open" ? (
        <>
          <div className="mb-4 flex flex-wrap gap-3">
            <input
              type="search"
              value={search}
              maxLength={80}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search name or HN- reference"
              aria-label="Search"
              className={cx(inputCls, "max-w-xs")}
            />
            <input
              value={locality}
              maxLength={120}
              onChange={(e) => set({ locality: e.target.value })}
              placeholder="Locality"
              aria-label="Locality"
              className={cx(inputCls, "max-w-48")}
            />
          </div>
          {!work.data ? (
            <Loading />
          ) : work.data.items.length === 0 ? (
            <Empty title="Nobody needs review">{q || locality ? "No flagged citizen matches these filters." : "Every flag in your catchment has been handled."}</Empty>
          ) : (
            <>
              <ul className={cx("flex flex-col gap-3", work.loading && "opacity-60")}>
                {work.data.items.map((item) => (
                  <Citizen key={item.citizen.id} item={item} onChanged={work.reload} />
                ))}
              </ul>
              {work.data.total_citizens > work.data.items.length && (
                <p className="mt-3 text-xs text-ink-soft">
                  Showing the {work.data.items.length} most urgent of {work.data.total_citizens}. Resolve these to see the rest.
                </p>
              )}
            </>
          )}
        </>
      ) : (
        <Card title={feed.data ? `Flags raised in the last ${feed.data.days} days` : "Recent flags"}>
          {!feed.data ? (
            feed.error ? <p className="text-sm text-danger">{feed.error}</p> : <Loading />
          ) : feed.data.items.length === 0 ? (
            <Empty title="No flags in this period" />
          ) : (
            <ul className="divide-y divide-line">
              {feed.data.items.map((f) => (
                <li key={f.processed_id} className="flex flex-wrap items-start gap-3 py-3 text-sm">
                  <SeverityBadge severity={f.severity} />
                  <div className="min-w-48 flex-1">
                    <PersonLine person={f.citizen} />
                    <p className="text-ink">{f.signal}</p>
                  </div>
                  <div className="text-right text-xs text-ink-soft">
                    <p>{fmtDateTime(f.measured_at)}</p>
                    <p>{f.status === "open" ? "Open" : `${f.status === "reviewed" ? "Reviewed" : "Dismissed"}${f.reviewed_by ? ` by ${f.reviewed_by}` : ""}`}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}
    </>
  );
}
