import { useEffect, useRef, useState } from "react";
import { CitizenWorkCard, PersonLine, workerState } from "../../components/app/phc";
import { Card, Empty, Loading, PageHeader, SeverityBadge, Tabs, cx, inputCls } from "../../components/app/ui";
import { fmtDateTime } from "../../lib/format";
import { oneOf, textParam, useQueryState } from "../../lib/params";
import { useDebounced } from "../../lib/useDebounced";
import { useResource } from "../../lib/useResource";
import { getFeed, getWorklist } from "../../services/phc";

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
                  <CitizenWorkCard key={item.citizen.id} item={item} onChanged={work.reload} />
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
