import { useEffect, useState } from "react";
import { PersonLine, workerState } from "../../components/app/phc";
import { Btn, Card, Empty, Loading, PageHeader, SeverityBadge, Tabs, cx, inputCls } from "../../components/app/ui";
import { fmtAgo } from "../../lib/format";
import { intParam, oneOf, textParam, useQueryState } from "../../lib/params";
import { useResource } from "../../lib/useResource";
import { getDirectory, type Engagement } from "../../services/phc";

const STATUSES = ["attention", "never_logged", "silent", "ok"] as const;
const PAGE = 50;

const STATUS_LABEL: Record<Engagement, string> = {
  attention: "Needs attention",
  never_logged: "Never logged",
  silent: "Gone quiet",
  ok: "Logging",
};

export function Citizens() {
  const { params, set } = useQueryState();
  const status = oneOf(params.get("status"), STATUSES, null);
  const locality = textParam(params.get("locality"), 120);
  const offset = intParam(params.get("offset"), 0, 0, 100_000);
  const [search, setSearch] = useState(() => textParam(params.get("q"), 80));
  const [q, setQ] = useState(search);
  useEffect(() => {
    if (search === q) return;
    const t = window.setTimeout(() => {
      setQ(search);
      set({ q: search, offset: null });
    }, 300);
    return () => window.clearTimeout(t);
  }, [search, q, set]);

  const query = { q, locality, status, limit: PAGE, offset };
  const dir = useResource((s) => getDirectory(query, s), JSON.stringify(query));
  const blocked = workerState(dir);
  if (blocked) return blocked;
  const d = dir.data;

  return (
    <>
      <PageHeader
        title="Citizens"
        lead={d ? `Everyone registered to your centre, ${d.catchment_total} in all. Sorted by what is worth opening first.` : undefined}
      />
      {d && (
        <Tabs
          label="Status"
          value={status ?? "all"}
          onChange={(v) => set({ status: v === "all" ? null : v, offset: null })}
          tabs={[
            { id: "all" as const, label: `All (${d.catchment_total})` },
            ...STATUSES.map((s) => ({ id: s, label: `${STATUS_LABEL[s]} (${d.counts[s]})` })),
          ]}
        />
      )}
      <div className="mb-4 flex flex-wrap gap-3">
        <input type="search" value={search} maxLength={80} onChange={(e) => setSearch(e.target.value)} placeholder="Search name or HN- reference" aria-label="Search" className={cx(inputCls, "max-w-xs")} />
        <select aria-label="Locality" value={locality} onChange={(e) => set({ locality: e.target.value, offset: null })} className={cx(inputCls, "w-auto")}>
          <option value="">All localities</option>
          {d?.localities.map((l) => (
            <option key={l.locality} value={l.locality === "Unspecified" ? "" : l.locality} disabled={l.locality === "Unspecified"}>
              {l.locality} ({l.citizens})
            </option>
          ))}
        </select>
      </div>

      {!d ? (
        <Loading />
      ) : d.items.length === 0 ? (
        <Empty title="No citizens match" />
      ) : (
        <Card className={cx("overflow-x-auto p-0", dir.loading && "opacity-60")}>
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="border-b border-line text-xs uppercase tracking-wide text-ink-soft">
              <tr>
                <th className="px-4 py-3 font-medium">Citizen</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Open flags</th>
                <th className="px-4 py-3 font-medium">Last reading</th>
                <th className="px-4 py-3 font-medium">Age</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {d.items.map((c) => (
                <tr key={c.citizen.id}>
                  <td className="px-4 py-3">
                    <PersonLine person={c.citizen} />
                  </td>
                  <td className="px-4 py-3 text-ink">{STATUS_LABEL[c.status]}</td>
                  <td className="px-4 py-3">
                    {c.open_flags > 0 && c.worst_severity ? (
                      <span className="flex items-center gap-2">
                        <SeverityBadge severity={c.worst_severity} /> {c.open_flags}
                      </span>
                    ) : (
                      <span className="text-ink-soft">—</span>
                    )}
                  </td>
                  <td className={cx("px-4 py-3", c.status === "silent" ? "text-warn" : "text-ink-soft")}>
                    {c.last_reading_at ? fmtAgo(c.last_reading_at) : `never (joined ${fmtAgo(c.joined_at)})`}
                  </td>
                  <td className="px-4 py-3 text-ink-soft">{c.age ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
      {d && d.total > PAGE && (
        <nav aria-label="Pages" className="mt-4 flex items-center justify-between text-sm text-ink-soft">
          <span>
            {offset + 1}–{Math.min(offset + PAGE, d.total)} of {d.total}
          </span>
          <div className="flex gap-2">
            <Btn disabled={offset === 0} onClick={() => set({ offset: Math.max(0, offset - PAGE) || null })}>
              Previous
            </Btn>
            <Btn disabled={offset + PAGE >= d.total} onClick={() => set({ offset: offset + PAGE })}>
              Next
            </Btn>
          </div>
        </nav>
      )}
      {d && <p className="mt-3 text-xs text-ink-soft">"Gone quiet": no reading in {d.silent_after_days} days. Counts cover your whole catchment, not just this page.</p>}
    </>
  );
}
