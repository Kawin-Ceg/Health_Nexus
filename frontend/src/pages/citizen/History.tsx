import { useState } from "react";
import { CircleCheck, Clock, Eye, UserCheck } from "lucide-react";
import { Detail, Modal } from "../../components/app/visits";
import { Btn, Card, ClearFilters, Empty, ErrorNote, Loading, PageHeader, SearchInput, SeverityBadge, Status, cx, inputCls } from "../../components/app/ui";
import { fmtStamp } from "../../lib/format";
import { intParam, oneOf, textParam, useQueryState } from "../../lib/params";
import { useDebounced } from "../../lib/useDebounced";
import { useResource } from "../../lib/useResource";
import { getHistory, getMetrics, type Metric, type Reading } from "../../services/health";

const WINDOWS = [
  { id: "all", label: "All time" },
  { id: "7", label: "Last 7 days" },
  { id: "30", label: "Last 30 days" },
  { id: "90", label: "Last 3 months" },
  { id: "365", label: "Last year" },
] as const;
const STATES = [
  { id: "normal", label: "Normal" },
  { id: "awaiting", label: "Awaiting review" },
  { id: "reviewed", label: "Reviewed" },
] as const;
const PAGE_SIZE = 20;

const SLOT: Record<string, string> = { morning: "morning", afternoon: "afternoon", evening: "evening", night: "night" };

function sourceOf(r: Reading) {
  if (r.source === "phc") return `Examination by ${r.recorded_by ?? "your health worker"}`;
  if (r.source === "watch") return r.watch_slot ? `Smartwatch, ${SLOT[r.watch_slot]}` : "Smartwatch";
  return "Entered by you";
}

function ResultStatus({ r }: { r: Reading }) {
  if (r.flagged && r.severity) return <SeverityBadge severity={r.severity} />;
  return <Status tone="success" icon={CircleCheck}>Normal</Status>;
}

function ReviewStatus({ r }: { r: Reading }) {
  if (!r.flagged) return <span className="text-sm text-ink-muted">Not needed</span>;
  if (r.reviewed) return <Status tone="success" icon={UserCheck}>{r.reviewed_by ?? "Reviewed"}</Status>;
  return <Status tone="warn" icon={Clock}>Awaiting review</Status>;
}

export function History() {
  const { params, set } = useQueryState();
  const { data: info } = useResource(() => getMetrics(), "metrics");
  const metricKeys = (info?.metrics ?? []).map((m) => m.key);

  const window = oneOf(params.get("days"), WINDOWS.map((w) => w.id), "all");
  const metric = info ? oneOf(params.get("metric"), metricKeys, null) : null;
  const state = oneOf(params.get("state"), STATES.map((s) => s.id), null);
  const reviewer = params.get("reviewer");
  const page = intParam(params.get("page"), 1, 1, 10_000);
  const [search, setSearch] = useState(textParam(params.get("q"), 80));
  const q = useDebounced(search.trim());
  const query = { page, page_size: PAGE_SIZE, metric, days: window === "all" ? null : Number(window), state, reviewer, q };

  const { data, error, loading, reload } = useResource((signal) => getHistory(query, signal), JSON.stringify(query));
  const [openId, setOpenId] = useState<string | null>(null);

  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;
  const byKey = new Map((info?.metrics ?? []).map((m) => [m.key, m]));
  const filtered = !!(search || metric || state || reviewer || window !== "all");
  const clear = () => {
    setSearch("");
    set({ metric: null, state: null, reviewer: null, days: null, page: null, q: null });
  };
  const opened = data?.items.find((r) => r.id === openId) ?? null;

  return (
    <>
      <PageHeader title="History" lead="Every reading, newest first. Open one to see all its values." />
      <div className="mb-3 grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto]">
        <SearchInput
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            set({ page: null });
          }}
          onClear={() => setSearch("")}
          placeholder="Search health worker, symptom, smartwatch or examination"
          aria-label="Search history"
        />
        <ClearFilters active={filtered} onClear={clear} />
      </div>
      <div className="mb-5 grid grid-cols-2 gap-3 md:grid-cols-4">
        <select aria-label="Status" className={cx(inputCls, "px-3")} value={state ?? ""} onChange={(e) => set({ state: e.target.value, page: null })}>
          <option value="">Every status</option>
          {STATES.map((s) => (
            <option key={s.id} value={s.id}>{s.label}</option>
          ))}
        </select>
        <select aria-label="Days" className={cx(inputCls, "px-3")} value={window} onChange={(e) => set({ days: e.target.value === "all" ? null : e.target.value, page: null })}>
          {WINDOWS.map((w) => (
            <option key={w.id} value={w.id}>{w.label}</option>
          ))}
        </select>
        <select aria-label="Reviewed by" className={cx(inputCls, "px-3")} value={reviewer ?? ""} onChange={(e) => set({ reviewer: e.target.value, page: null })}>
          <option value="">Any health worker</option>
          {data?.reviewers.map((r) => (
            <option key={r.id} value={r.id}>{r.name}</option>
          ))}
        </select>
        <select aria-label="Measurement" className={cx(inputCls, "px-3")} value={metric ?? ""} onChange={(e) => set({ metric: e.target.value, page: null })}>
          <option value="">All measurements</option>
          {info?.metrics.map((m) => (
            <option key={m.key} value={m.key}>{m.label}</option>
          ))}
        </select>
      </div>

      {error ? (
        <ErrorNote message={error} onRetry={reload} />
      ) : !data ? (
        <Loading />
      ) : data.items.length === 0 ? (
        <Empty title={filtered ? "No readings match these filters" : "No readings yet"} />
      ) : (
        <Card className={cx("overflow-x-auto p-0!", loading && "opacity-60")}>
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="border-b border-line text-xs font-semibold uppercase tracking-[0.06em] text-ink-soft">
              <tr>
                <th className="w-12 px-4 py-3 font-semibold">#</th>
                <th className="px-4 py-3 font-semibold">When</th>
                <th className="px-4 py-3 font-semibold">Source</th>
                <th className="px-4 py-3 font-semibold">Result</th>
                <th className="px-4 py-3 font-semibold">Reviewed by</th>
                <th className="w-24 px-4 py-3"><span className="visually-hidden">Open</span></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {data.items.map((r, i) => (
                <tr key={r.id} onClick={() => setOpenId(r.id)} className="cursor-pointer hover:bg-paper">
                  <td className="px-4 py-3.5 tabular-nums text-ink-muted">{(page - 1) * PAGE_SIZE + i + 1}</td>
                  <td className="px-4 py-3.5 font-medium text-ink">{fmtStamp(r.measured_at)}</td>
                  <td className="px-4 py-3.5 text-ink-soft">{sourceOf(r)}</td>
                  <td className="px-4 py-3.5"><ResultStatus r={r} /></td>
                  <td className="px-4 py-3.5"><ReviewStatus r={r} /></td>
                  <td className="px-4 py-3.5">
                    <button
                      type="button"
                      onClick={(ev) => {
                        ev.stopPropagation();
                        setOpenId(r.id);
                      }}
                      className="inline-flex min-h-9 items-center gap-1.5 rounded-lg px-2.5 text-sm font-medium text-blue-700 hover:bg-blue-50 focus-visible:outline-2 focus-visible:outline-blue-700"
                    >
                      <Eye size={15} aria-hidden="true" /> View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {data && data.total > PAGE_SIZE && (
        <nav aria-label="Pages" className="mt-4 flex items-center justify-between text-sm text-ink-soft">
          <span>
            Page {page} of {pages} · {data.total} readings
          </span>
          <div className="flex gap-2">
            <Btn disabled={page <= 1} onClick={() => set({ page: page - 1 })}>Newer</Btn>
            <Btn disabled={page >= pages} onClick={() => set({ page: page + 1 })}>Older</Btn>
          </div>
        </nav>
      )}

      {opened && <ReadingDetails r={opened} byKey={byKey} focus={metric} onClose={() => setOpenId(null)} />}
    </>
  );
}

function ReadingDetails({ r, byKey, focus, onClose }: { r: Reading; byKey: Map<string, Metric>; focus: string | null; onClose: () => void }) {
  return (
    <Modal title={fmtStamp(r.measured_at)} onClose={onClose} wide>
      <div className="flex flex-col gap-5">
        <div className="flex flex-wrap items-center gap-5">
          <ResultStatus r={r} />
          <ReviewStatus r={r} />
        </div>
        {r.signal && <p className="text-base text-ink">{r.signal}</p>}
        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {Object.entries(r.vitals).map(([k, v]) => {
            const m = byKey.get(k);
            const off = m?.normal ? v < m.normal[0] || v > m.normal[1] : false;
            return (
              <li key={k} className={cx("rounded-2xl border bg-surface p-3", off ? "border-warn/60" : "border-line", focus === k && "ring-2 ring-ink/20")}>
                <p className="text-xs text-ink-muted">{m?.label ?? k}</p>
                <p className="font-display text-2xl tabular-nums text-ink">
                  {m ? v.toFixed(m.decimals) : v} <span className="font-sans text-xs text-ink-soft">{m?.unit}</span>
                </p>
                {m?.normal && (
                  <p className={cx("text-xs", off ? "font-semibold text-warn" : "text-ink-muted")}>
                    {off ? "Outside" : "Within"} {m.normal[0]}–{m.normal[1]}
                  </p>
                )}
              </li>
            );
          })}
        </ul>
        <dl className="grid gap-4 sm:grid-cols-2">
          <Detail label="Source">{sourceOf(r)}</Detail>
          {r.location && <Detail label="Place">{r.location}</Detail>}
          {r.flagged && <Detail label="Reviewed by">{r.reviewed ? r.reviewed_by ?? "Your health centre" : "Not yet"}</Detail>}
          {r.reviewed_at && <Detail label="Reviewed on">{fmtStamp(r.reviewed_at)}</Detail>}
          {r.symptoms.length > 0 && <Detail label="Symptoms"><span className="capitalize">{r.symptoms.join(", ")}</span></Detail>}
        </dl>
      </div>
    </Modal>
  );
}
