import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Phone } from "lucide-react";
import { BasisTag, ScoreBreakdown } from "../../components/app/ModelInsights";
import { BookVisitForm, NoFacility, ResolveControls } from "../../components/app/phc";
import { TrendChart } from "../../components/app/TrendChart";
import { Btn, Card, Empty, ErrorNote, Loading, PageHeader, SeverityBadge, Stat, VisitBadge, cx } from "../../components/app/ui";
import { fmtDate, fmtDateTime, fmtVisit, plural } from "../../lib/format";
import { oneOf, useQueryState } from "../../lib/params";
import { paths } from "../../lib/routes";
import { useResource } from "../../lib/useResource";
import { getMetrics } from "../../services/health";
import { getRecord, resolveCitizen } from "../../services/phc";

const WINDOWS = ["30", "90", "180", "365"] as const;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function CitizenRecord() {
  const { userId = "" } = useParams();
  const { params, set } = useQueryState();
  const days = Number(oneOf(params.get("days"), WINDOWS, "90"));
  const validId = UUID.test(userId);
  const record = useResource(
    (s) => (validId ? Promise.all([getRecord(userId, days, s), getMetrics()]) : Promise.reject(new Error("bad id"))),
    `${userId}:${days}`,
  );
  const [chosen, setChosen] = useState<string | null>(null);
  const [booking, setBooking] = useState(false);

  const [r, info] = record.data ?? [null, null];
  const metrics = useMemo(() => new Map((info?.metrics ?? []).map((m) => [m.key, m])), [info]);

  if (!validId || record.status === 404) {
    return (
      <Empty title="Citizen not found">
        <Link to={paths.phcCitizens} className="text-brand underline">Back to citizens</Link>
      </Empty>
    );
  }
  if (record.status === 409 && record.error) return <NoFacility message={record.error} />;
  if (record.error && !record.data) return <ErrorNote message={record.error} onRetry={record.reload} />;
  if (!r || !info) return <Loading label="Loading record" />;

  const id = r.identity;
  const charted = r.vitals.map((v) => metrics.get(v.key)).filter((m) => m !== undefined);
  const metric = charted.find((m) => m.key === chosen) ?? charted[0];
  const points = metric
    ? r.timeline
        .filter((t) => t.vitals[metric.key] !== undefined)
        .map((t) => ({ measured_at: t.measured_at, value: t.vitals[metric.key], flagged: t.flagged }))
        .reverse()
    : [];
  const person = { id: id.id, ref: id.ref, name: id.name, phone: id.phone, area: id.area };
  const before = r.unresolved_before_window;

  return (
    <>
      <Link to={paths.phcCitizens} className="mb-3 inline-flex items-center gap-1 text-sm text-ink-soft hover:text-ink">
        <ArrowLeft size={16} aria-hidden="true" /> Citizens
      </Link>
      <PageHeader
        title={id.name}
        lead={
          <span className="flex flex-wrap gap-x-3">
            <span className="font-mono">{id.ref}</span>
            {id.age !== null && <span>{id.age} yrs{id.gender ? `, ${id.gender.replace(/_/g, " ")}` : ""}</span>}
            {id.area && <span>{id.area}{id.pincode ? ` ${id.pincode}` : ""}</span>}
          </span>
        }
        actions={
          <>
            {id.phone && (
              <a href={`tel:${id.phone.replace(/[^\d+]/g, "")}`} className="inline-flex min-h-11 items-center gap-2 rounded-2xl border border-line px-4 text-sm font-semibold text-ink">
                <Phone size={16} aria-hidden="true" /> {id.phone}
              </a>
            )}
            <Btn tone="primary" onClick={() => setBooking((b) => !b)}>Book visit</Btn>
          </>
        }
      />
      {booking && (
        <div className="mb-6">
          <BookVisitForm citizen={person} onCancel={() => setBooking(false)} onBooked={() => { setBooking(false); record.reload(); }} />
        </div>
      )}

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <label className="text-sm text-ink-soft" htmlFor="window">Showing the last</label>
        <select id="window" value={String(days)} onChange={(e) => set({ days: e.target.value })} className="min-h-11 rounded-xl border border-line bg-surface px-2 text-sm">
          {WINDOWS.map((w) => <option key={w} value={w}>{w} days</option>)}
        </select>
        <span className="text-xs text-ink-soft">{fmtDate(r.window.start)} – {fmtDate(r.window.end)}. Every figure below covers this period.</span>
      </div>

      {(before.open_flags > 0 || before.visits_without_outcome > 0) && (
        <div role="note" className="mb-6 rounded-2xl border border-warn/40 bg-warn/10 p-4 text-sm text-ink">
          <strong>From before this period:</strong>{" "}
          {before.open_flags > 0 && `${plural(before.open_flags, "unresolved flag")} (oldest ${fmtDate(before.oldest_flag_at!)}). `}
          {before.visits_without_outcome > 0 && `${plural(before.visits_without_outcome, "visit")} with no outcome recorded.`}
        </div>
      )}

      <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Readings" value={r.counts.readings} />
        <Stat label="Flagged" value={r.counts.flags} />
        <Stat label="Still open" value={r.counts.open_flags} tone={r.counts.open_flags ? "danger" : undefined} />
        <Stat label="Visits" value={r.counts.visits} />
      </div>

      {r.counts.open_flags + before.open_flags > 0 && (
        <Card className="mb-6" title="Open flags">
          <ResolveControls reviewLabel="Resolve all open flags" onResolve={async (body) => { await resolveCitizen(id.id, body); record.reload(); }} />
        </Card>
      )}

      <div className="mb-6 grid gap-6 lg:grid-cols-5">
        <Card className="lg:col-span-3" title="Latest against their own baseline">
          {r.vitals.length === 0 ? (
            <Empty title="No readings in this period" />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[420px] text-left text-sm">
                <thead className="text-xs uppercase tracking-wide text-ink-soft">
                  <tr><th className="py-2 font-medium">Vital</th><th className="py-2 font-medium">Latest</th><th className="py-2 font-medium">Their usual (model baseline)</th><th className="py-2 font-medium">Deviation</th></tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {r.vitals.map((v) => {
                    const m = metrics.get(v.key);
                    if (!m) return null;
                    const far = v.z_score !== null && Math.abs(v.z_score) >= 2;
                    return (
                      <tr key={v.key}>
                        <td className="py-2 text-ink">{m.label}</td>
                        <td className={cx("py-2 tabular-nums", v.position !== "normal" ? "font-semibold text-sev-high" : "text-ink")}>
                          {v.latest.toFixed(m.decimals)} {m.unit}
                        </td>
                        <td className="py-2 tabular-nums text-ink-soft">
                          {v.baseline ? `${v.baseline.usual.toFixed(m.decimals)} ± ${v.baseline.spread.toFixed(m.decimals)} (last ${v.baseline.n})` : `too few readings (need ${r.min_baseline_readings})`}
                        </td>
                        <td className={cx("py-2 tabular-nums", far ? "font-semibold text-sev-high" : "text-ink-soft")}>
                          {v.z_score === null ? "—" : `${v.z_score > 0 ? "+" : ""}${v.z_score} SD`}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>
        <Card className="lg:col-span-2" title="Health profile">
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
            <dt className="text-ink-soft">Conditions</dt><dd className="text-ink">{id.existing_conditions.join(", ") || "None recorded"}</dd>
            <dt className="text-ink-soft">Medications</dt><dd className="text-ink">{id.current_medications.join(", ") || "None recorded"}</dd>
            <dt className="text-ink-soft">Blood group</dt><dd className="text-ink">{id.blood_group ?? "—"}</dd>
            <dt className="text-ink-soft">Emergency</dt><dd className="text-ink">{id.emergency_contact_name ? `${id.emergency_contact_name}, ${id.emergency_contact_phone}` : "—"}</dd>
            <dt className="text-ink-soft">Email</dt><dd className="break-all text-ink">{id.email}</dd>
            <dt className="text-ink-soft">Joined</dt><dd className="text-ink">{fmtDate(id.joined_at)}</dd>
          </dl>
        </Card>
      </div>

      {metric && points.length > 0 && (
        <Card
          className="mb-6"
          title={`${metric.label} in this period`}
          aside={charted.length > 1 && (
            <select aria-label="Measurement to chart" value={metric.key} onChange={(e) => setChosen(e.target.value)} className="min-h-11 rounded-xl border border-line bg-surface px-2 text-sm">
              {charted.map((m) => <option key={m.key} value={m.key}>{m.label}</option>)}
            </select>
          )}
        >
          <TrendChart metric={metric} points={points} />
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Submissions" aside={r.timeline_truncated && <span className="text-xs text-warn">Newest {r.timeline_limit} of {r.counts.readings} shown</span>}>
          {r.timeline.length === 0 ? <Empty title="No readings in this period" /> : (
            <ul className="flex max-h-[32rem] flex-col divide-y divide-line overflow-y-auto">
              {r.timeline.map((t) => (
                <li key={t.reading_id} className="py-2 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-ink">{fmtDateTime(t.measured_at)}</span>
                    {t.severity && <SeverityBadge severity={t.severity} />}
                    {t.flagged && <span className="text-xs text-ink-soft">{t.resolution ? t.resolution : "open"}</span>}
                    {t.flagged && <BasisTag basis={t.basis} />}
                  </div>
                  {t.signal && <p className="text-sev-high">{t.signal}</p>}
                  {t.flagged && t.checks.length > 0 && (
                    <details className="mt-1">
                      <summary className="cursor-pointer text-xs font-semibold text-brand">Why it was flagged</summary>
                      <div className="mt-2">
                        <ScoreBreakdown checks={t.checks} metrics={metrics} who="worker" />
                      </div>
                    </details>
                  )}
                  <p className="text-xs text-ink-soft">
                    {Object.entries(t.vitals).map(([k, v]) => `${metrics.get(k)?.label ?? k} ${v.toFixed(metrics.get(k)?.decimals ?? 0)}`).join(" · ")}
                    {t.symptoms.length > 0 && ` · ${t.symptoms.join(", ")}`}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <div className="flex flex-col gap-6">
          <Card title="Visits">
            {r.upcoming_visits.length + r.visits.length === 0 ? <p className="text-sm text-ink-soft">None in this period.</p> : (
              <ul className="flex flex-col gap-2 text-sm">
                {r.upcoming_visits.map((v) => (
                  <li key={v.id} className="flex flex-wrap items-center gap-2"><span className="text-ink">{fmtVisit(v.scheduled_for)}</span><VisitBadge state={v.state} /><span className="text-xs text-ink-soft">booked ahead</span></li>
                ))}
                {r.visits.map((v) => (
                  <li key={v.id} className="flex flex-wrap items-center gap-2"><span className="text-ink">{fmtVisit(v.scheduled_for)}</span><VisitBadge state={v.state} />{v.worker_name && <span className="text-xs text-ink-soft">{v.worker_name}</span>}</li>
                ))}
              </ul>
            )}
          </Card>
          <Card title={`Alerts sent (${r.counts.alerts})`}>
            {r.alerts.length === 0 ? <p className="text-sm text-ink-soft">None in this period.</p> : (
              <ul className="flex max-h-72 flex-col gap-2 overflow-y-auto text-sm">
                {r.alerts.map((a) => (
                  <li key={a.id}><p className="text-ink">{a.message}</p><p className="text-xs text-ink-soft">{fmtDateTime(a.created_at)}</p></li>
                ))}
              </ul>
            )}
            {r.counts.alerts > r.alerts.length && <p className="mt-2 text-xs text-ink-soft">Newest {r.alerts.length} of {r.counts.alerts} shown.</p>}
          </Card>
        </div>
      </div>
    </>
  );
}
