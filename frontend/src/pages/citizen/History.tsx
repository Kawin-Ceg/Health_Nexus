import { useState } from "react";
import { Trash2 } from "lucide-react";
import { Btn, Card, Empty, ErrorNote, Loading, PageHeader, SeverityBadge, cx } from "../../components/app/ui";
import { fmtDateTime } from "../../lib/format";
import { intParam, oneOf, useQueryState } from "../../lib/params";
import { useResource } from "../../lib/useResource";
import { errorMessage } from "../../services/api";
import { deleteReading, getHistory, getMetrics } from "../../services/health";

const WINDOWS = ["7", "30", "90", "365", "all"] as const;
const PAGE_SIZE = 20;

export function History() {
  const { params, set } = useQueryState();
  const { data: info } = useResource(() => getMetrics(), "metrics");
  const metricKeys = (info?.metrics ?? []).map((m) => m.key);

  // Clamped and validated: nothing unexpected from the URL reaches the API.
  const window = oneOf(params.get("days"), WINDOWS, "90");
  const metric = info ? oneOf(params.get("metric"), metricKeys, null) : null;
  const flaggedOnly = params.get("flagged") === "1";
  const page = intParam(params.get("page"), 1, 1, 10_000);
  const query = { page, page_size: PAGE_SIZE, metric, days: window === "all" ? null : Number(window), flagged_only: flaggedOnly };

  const { data, error, loading, reload } = useResource((signal) => getHistory(query, signal), JSON.stringify(query));
  const [confirming, setConfirming] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const remove = async (id: string) => {
    setDeleting(true);
    setActionError(null);
    try {
      await deleteReading(id);
      setConfirming(null);
      reload();
    } catch (e) {
      setActionError(errorMessage(e));
    } finally {
      setDeleting(false);
    }
  };

  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;
  const byKey = new Map((info?.metrics ?? []).map((m) => [m.key, m]));
  const selectCls = "min-h-11 rounded-xl border border-line bg-surface px-3 text-sm";

  return (
    <>
      <PageHeader title="History" lead="Your readings, newest first." />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <select aria-label="Measurement" className={selectCls} value={metric ?? ""} onChange={(e) => set({ metric: e.target.value, page: null })}>
          <option value="">All measurements</option>
          {info?.metrics.map((m) => (
            <option key={m.key} value={m.key}>
              {m.label}
            </option>
          ))}
        </select>
        <select aria-label="Time window" className={selectCls} value={window} onChange={(e) => set({ days: e.target.value, page: null })}>
          <option value="7">Last 7 days</option>
          <option value="30">Last 30 days</option>
          <option value="90">Last 90 days</option>
          <option value="365">Last year</option>
          <option value="all">All time</option>
        </select>
        <label className="flex items-center gap-2 text-sm text-ink">
          <input type="checkbox" checked={flaggedOnly} onChange={(e) => set({ flagged: e.target.checked ? "1" : null, page: null })} />
          Flagged only
        </label>
      </div>

      {actionError && <div className="mb-4"><ErrorNote message={actionError} /></div>}
      {error ? (
        <ErrorNote message={error} onRetry={reload} />
      ) : !data ? (
        <Loading />
      ) : data.items.length === 0 ? (
        <Empty title="No readings match these filters" />
      ) : (
        <Card className={cx("p-0", loading && "opacity-60")}>
          <ul className="divide-y divide-line">
            {data.items.map((r) => (
              <li key={r.id} className={cx("flex flex-wrap items-start gap-4 p-4", r.flagged && "border-l-4 border-l-sev-high")}>
                <div className="min-w-40">
                  <p className="text-sm font-semibold text-ink">{fmtDateTime(r.measured_at)}</p>
                  {r.flagged && r.severity && (
                    <div className="mt-1 flex flex-wrap items-center gap-2">
                      <SeverityBadge severity={r.severity} />
                      <span className="text-xs text-ink-soft">{r.reviewed ? "Reviewed" : "Awaiting review"}</span>
                    </div>
                  )}
                </div>
                <div className="flex-1">
                  <dl className="flex flex-wrap gap-x-5 gap-y-1 text-sm">
                    {Object.entries(r.vitals).map(([k, v]) => {
                      const m = byKey.get(k);
                      return (
                        <div key={k} className={cx(metric === k && "font-semibold")}>
                          <dt className="inline text-ink-soft">{m?.label ?? k}: </dt>
                          <dd className="inline tabular-nums text-ink">
                            {m ? v.toFixed(m.decimals) : v} {m?.unit}
                          </dd>
                        </div>
                      );
                    })}
                  </dl>
                  {r.signal && <p className="mt-1 text-sm text-sev-high">{r.signal}</p>}
                  {r.symptoms.length > 0 && <p className="mt-1 text-xs capitalize text-ink-soft">Symptoms: {r.symptoms.join(", ")}</p>}
                </div>
                {confirming === r.id ? (
                  <div className="flex items-center gap-2" role="group" aria-label="Confirm delete">
                    <span className="text-sm text-ink">Delete this reading?</span>
                    <Btn tone="danger" busy={deleting} onClick={() => void remove(r.id)}>
                      Delete
                    </Btn>
                    <Btn tone="ghost" onClick={() => setConfirming(null)}>
                      Keep
                    </Btn>
                  </div>
                ) : (
                  <Btn tone="ghost" onClick={() => setConfirming(r.id)} aria-label={`Delete reading from ${fmtDateTime(r.measured_at)}`}>
                    <Trash2 size={16} aria-hidden="true" /> Entered by mistake
                  </Btn>
                )}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {data && data.total > PAGE_SIZE && (
        <nav aria-label="Pages" className="mt-4 flex items-center justify-between text-sm text-ink-soft">
          <span>
            Page {page} of {pages} · {data.total} readings
          </span>
          <div className="flex gap-2">
            <Btn disabled={page <= 1} onClick={() => set({ page: page - 1 })}>
              Newer
            </Btn>
            <Btn disabled={page >= pages} onClick={() => set({ page: page + 1 })}>
              Older
            </Btn>
          </div>
        </nav>
      )}
    </>
  );
}
