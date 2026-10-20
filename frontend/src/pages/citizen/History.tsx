import { useState } from "react";
import { ChevronDown, CircleCheck, Clock, Trash2, UserCheck } from "lucide-react";
import { PopulationNote } from "../../components/app/ModelInsights";
import { Btn, Card, Empty, ErrorNote, Loading, PageHeader, SeverityBadge, cx } from "../../components/app/ui";
import { fmtAgo, fmtDateTime } from "../../lib/format";
import { SEVERITY } from "../../lib/severity";
import { intParam, oneOf, useQueryState } from "../../lib/params";
import { useResource } from "../../lib/useResource";
import { errorMessage } from "../../services/api";
import { deleteReading, getHistory, getMetrics } from "../../services/health";
import { useToast } from "../../components/app/Toaster";
import { useLabel, useT } from "../../i18n";

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
  const [open, setOpen] = useState<Set<string>>(new Set());
  const toggle = (id: string) =>
    setOpen((cur) => {
      const next = new Set(cur);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  const [deleting, setDeleting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const { notify } = useToast();
  const t = useT();
  const label = useLabel();
  const remove = async (id: string) => {
    setDeleting(true);
    setActionError(null);
    try {
      await deleteReading(id);
      notify({ tone: "success", title: t("history.deleted") });
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
  const selectCls = "min-h-11 rounded-2xl border border-line bg-surface px-3 text-sm";

  return (
    <>
      <PageHeader title={t("history.title")} lead={t("history.lead")} />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <select aria-label="Measurement" className={selectCls} value={metric ?? ""} onChange={(e) => set({ metric: e.target.value, page: null })}>
          <option value="">{t("history.all")}</option>
          {info?.metrics.map((m) => (
            <option key={m.key} value={m.key}>
              {label("vital", m.key, m.label)}
            </option>
          ))}
        </select>
        <select aria-label="Time window" className={selectCls} value={window} onChange={(e) => set({ days: e.target.value, page: null })}>
          <option value="7">{t("history.days7")}</option>
          <option value="30">{t("history.days30")}</option>
          <option value="90">{t("history.days90")}</option>
          <option value="365">{t("history.year")}</option>
          <option value="all">{t("history.allTime")}</option>
        </select>
        <label className="flex items-center gap-2 text-sm text-ink">
          <input type="checkbox" checked={flaggedOnly} onChange={(e) => set({ flagged: e.target.checked ? "1" : null, page: null })} />
          {t("history.flaggedOnly")}
        </label>
      </div>

      {actionError && <div className="mb-4"><ErrorNote message={actionError} /></div>}
      {error ? (
        <ErrorNote message={error} onRetry={reload} />
      ) : !data ? (
        <Loading />
      ) : data.items.length === 0 ? (
        <Empty title={t("history.none")} />
      ) : (
        <Card className={cx("p-0", loading && "opacity-60")}>
          <div className="hidden grid-cols-[minmax(0,1.2fr)_minmax(0,1.4fr)_minmax(0,1fr)_auto] gap-4 border-b border-line px-5 py-3 text-xs font-semibold uppercase tracking-[0.06em] text-ink-muted md:grid">
            <span>{t("history.when")}</span>
            <span>{t("history.result")}</span>
            <span>{t("history.worker")}</span>
            <span className="w-28" />
          </div>
          <ul className="divide-y divide-line">
            {data.items.map((r) => {
              const isOpen = open.has(r.id);
              const tone = r.flagged && r.severity ? SEVERITY[r.severity] : null;
              return (
                <li key={r.id} className={cx("border-l-4", tone ? tone.border : "border-l-transparent")}>
                  <div className="grid gap-3 px-5 py-4 md:grid-cols-[minmax(0,1.2fr)_minmax(0,1.4fr)_minmax(0,1fr)_auto] md:items-center md:gap-4">
                    <div className="flex items-center gap-3">
                      <span className={cx("h-2.5 w-2.5 shrink-0 rounded-full", tone ? tone.dot : "bg-success")} aria-hidden="true" />
                      <span>
                        <span className="block text-sm font-semibold text-ink">{fmtDateTime(r.measured_at)}</span>
                        <span className="block text-xs text-ink-muted">
                          {fmtAgo(r.measured_at)} ·{" "}
                          {r.source === "phc"
                            ? `Examination by ${r.recorded_by ?? "your health worker"}`
                            : r.source === "watch"
                              ? `Smartwatch${r.watch_slot ? `, ${r.watch_slot}` : ""}`
                              : "Entered by you"}
                        </span>
                      </span>
                    </div>
                    <div className="min-w-0">
                      {r.flagged && r.severity ? (
                        <>
                          <SeverityBadge severity={r.severity} />
                          {r.signal && <p className="mt-1 truncate text-xs text-ink-soft">{r.signal}</p>}
                        </>
                      ) : (
                        <span className="inline-flex items-center gap-1 rounded-full bg-success-soft px-2 py-0.5 text-xs font-semibold text-success">
                          <CircleCheck size={12} aria-hidden="true" /> {t("history.normal")}
                        </span>
                      )}
                    </div>
                    <div className="text-sm">
                      {!r.flagged ? (
                        <span className="text-ink-muted">{t("history.notNeeded")}</span>
                      ) : r.reviewed ? (
                        <span className="inline-flex items-center gap-1.5 text-success">
                          <UserCheck size={16} aria-hidden="true" /> {t("history.reviewed")}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 text-warn">
                          <Clock size={16} aria-hidden="true" /> {t("history.awaiting")}
                        </span>
                      )}
                    </div>
                    <Btn
                      tone="ghost"
                      className="w-28 justify-self-start md:justify-self-end"
                      aria-expanded={isOpen}
                      aria-controls={`reading-${r.id}`}
                      onClick={() => toggle(r.id)}
                    >
                      {isOpen ? t("history.less") : t("history.more")}
                      <ChevronDown size={16} className={cx("transition-transform", isOpen && "rotate-180")} aria-hidden="true" />
                    </Btn>
                  </div>

                  {isOpen && (
                    <div id={`reading-${r.id}`} className="border-t border-line bg-paper px-5 py-5">
                      <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
                        {Object.entries(r.vitals).map(([k, v]) => {
                          const m = byKey.get(k);
                          const off = m?.normal ? v < m.normal[0] || v > m.normal[1] : false;
                          return (
                            <li key={k} className={cx("rounded-2xl border bg-surface p-3", off ? "border-warn/50" : "border-line", metric === k && "ring-2 ring-ink/20")}>
                              <p className="text-xs text-ink-muted">{label("vital", k, m?.label)}</p>
                              <p className="font-display text-2xl tabular-nums text-ink">
                                {m ? v.toFixed(m.decimals) : v} <span className="font-sans text-xs text-ink-soft">{m?.unit}</span>
                              </p>
                              {m?.normal && (
                                <p className={cx("text-xs", off ? "text-warn" : "text-ink-muted")}>
                                  {off ? t("history.outsideRange") : t("history.within")} {m.normal[0]}–{m.normal[1]}
                                </p>
                              )}
                            </li>
                          );
                        })}
                      </ul>
                      {r.source === "phc" && (
                        <p className="mt-4 text-sm text-ink-soft">
                          Recorded by {r.recorded_by ?? "your health worker"}
                          {r.location ? ` at ${r.location}` : ""}.
                        </p>
                      )}
                      {r.signal && <p className="mt-4 text-sm text-ink">{r.signal}</p>}
                      <PopulationNote check={r.population} className="mt-4" />
                      {r.symptoms.length > 0 && (
                        <div className="mt-4 flex flex-wrap items-center gap-2">
                          <span className="text-xs font-semibold uppercase tracking-[0.06em] text-ink-muted">{t("history.symptoms")}</span>
                          {r.symptoms.map((s) => (
                            <span key={s} className="rounded-full border border-line bg-surface px-3 py-1 text-xs capitalize text-ink">
                              {label("symptom", s, s)}
                            </span>
                          ))}
                        </div>
                      )}
                      <div className="mt-5 flex flex-wrap items-center justify-end gap-2 border-t border-line pt-4">
                        {confirming === r.id ? (
                          <div className="flex items-center gap-2" role="group" aria-label="Confirm delete">
                            <span className="text-sm text-ink">{t("history.deleteAsk")}</span>
                            <Btn tone="danger" busy={deleting} onClick={() => void remove(r.id)}>
                              {t("history.delete")}
                            </Btn>
                            <Btn tone="ghost" onClick={() => setConfirming(null)}>
                              {t("history.keep")}
                            </Btn>
                          </div>
                        ) : r.source === "phc" ? null : (
                          <Btn tone="ghost" onClick={() => setConfirming(r.id)} aria-label={`Delete reading from ${fmtDateTime(r.measured_at)}`}>
                            <Trash2 size={16} aria-hidden="true" /> {t("history.mistake")}
                          </Btn>
                        )}
                      </div>
                    </div>
                  )}
                </li>
              );
            })}
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
