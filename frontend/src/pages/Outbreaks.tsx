import "leaflet/dist/leaflet.css";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { Circle, MapContainer, TileLayer, Tooltip as MapTooltip } from "react-leaflet";
import { CheckCircle2, Eye, HelpCircle, Megaphone, RefreshCw, X, XCircle } from "lucide-react";
import { Btn, Card, Empty, ErrorNote, Labelled, Loading, PageHeader, SearchInput, cx, inputCls } from "../components/app/ui";
import { useToast } from "../components/app/Toaster";
import { useAuth } from "../context/AuthContext";
import { fmtAgo, fmtDate, fmtDateTime } from "../lib/format";
import { paths } from "../lib/routes";
import { useResource } from "../lib/useResource";
import { errorMessage } from "../services/api";
import { acknowledgeCluster, getClusters, reviewCluster, runClustering, type Cluster, type Verdict } from "../services/outbreaks";

const SYNDROME: Record<Cluster["syndrome"], string> = {
  febrile: "Fever",
  respiratory: "Respiratory",
  gastrointestinal: "Stomach and gut",
};

const colour = (c: Cluster) => (c.outbreak ? "rgb(var(--hn-sev-critical))" : "rgb(var(--hn-sev-moderate))");

const PERIODS = [
  { days: 0, label: "Latest check" },
  { days: 7, label: "Last 7 days" },
  { days: 30, label: "Last 30 days" },
  { days: 90, label: "Last 3 months" },
  { days: 180, label: "Last 6 months" },
    ];

const VERDICT: Record<Verdict, { label: string; cls: string; icon: typeof CheckCircle2 }> = {
  confirmed: { label: "Real outbreak", cls: "bg-red-50 text-red-800", icon: CheckCircle2 },
  false_alarm: { label: "False alarm", cls: "bg-green-50 text-green-800", icon: XCircle },
  unsure: { label: "Unsure", cls: "bg-paper-raised text-ink-soft", icon: HelpCircle },
};

function Pill({ className, children }: { className: string; children: ReactNode }) {
  return <span className={cx("inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold", className)}>{children}</span>;
}

function SeverityPill({ c }: { c: Cluster }) {
  return c.outbreak ? (
    <Pill className="bg-red-50 text-red-800">
      Possible outbreak
    </Pill>
  ) : (
    <Pill className="bg-amber-50 text-amber-800">
      Watch
    </Pill>
  );
}

function StatusPills({ c }: { c: Cluster }) {
  const v = c.feedback ? VERDICT[c.feedback] : null;
  return (
    <span className="flex flex-col items-start gap-1">
      {c.current ? <Pill className="bg-sky-50 text-sky-800">Active</Pill> : <Pill className="bg-paper-raised text-ink-soft">Ended</Pill>}
      {c.acknowledged_at && <Pill className="bg-violet-50 text-violet-800">Seen</Pill>}
      {v && (
        <Pill className={v.cls}>
          <v.icon size={12} aria-hidden="true" /> {v.label}
        </Pill>
      )}
    </span>
  );
}

export function Outbreaks() {
  const { user } = useAuth();
  const admin = user?.role === "admin";
  const [days, setDays] = useState(0);
  const res = useResource((s) => getClusters(days, s), `clusters-${days}`);
  const [running, setRunning] = useState(false);
  const [search, setSearch] = useState("");
  const [severity, setSeverity] = useState<"all" | "outbreak" | "watch">("all");
  const [openId, setOpenId] = useState<string | null>(null);
  const { notify } = useToast();
  const d = res.data;

  const rows = useMemo(() => {
    const q = search.trim().toLowerCase();
    return (d?.items ?? []).filter(
      (c) =>
        (severity === "all" || (severity === "outbreak") === c.outbreak) &&
        (!q || `${SYNDROME[c.syndrome]} ${c.region} ${c.district ?? ""} ${Object.keys(c.localities).join(" ")} ${Object.keys(c.symptoms).join(" ")}`.toLowerCase().includes(q)),
    );
  }, [d, search, severity]);
  const open = d?.items.find((c) => c.id === openId) ?? null;

  const runNow = async () => {
    setRunning(true);
    try {
      const out = await runClustering();
      notify({ tone: "info", title: "Clustering finished", body: `${out.items.length} cluster${out.items.length === 1 ? "" : "s"} found` });
      res.reload();
    } catch (e) {
      notify({ tone: "alert", title: "Clustering failed", body: errorMessage(e) });
    } finally {
      setRunning(false);
    }
  };

  return (
    <>
      <PageHeader
        title="Outbreak signals"
        lead={
          d
            ? `Places where at least ${d.min_people} people reported the same kind of illness within about ${d.radius_km} km and a few days of each other, in the last ${d.window_days} days. Only citizens who allow community monitoring are counted.`
            : undefined
        }
        actions={
          admin && (
            <Btn busy={running} onClick={() => void runNow()}>
              <RefreshCw size={16} aria-hidden="true" /> Run now
            </Btn>
          )
        }
      />
      {res.error && <ErrorNote message={res.error} onRetry={res.reload} />}
      {!d ? (
        !res.error && <Loading />
      ) : (
        <>
          <p className="mb-4 text-sm text-ink-soft">
            {d.last_run_at ? `Last checked ${fmtAgo(d.last_run_at)}. Checks run every 6 hours.` : "No check has run yet."}
          </p>

          <Card className="mb-8 overflow-hidden p-0!">
            {rows.length === 0 ? (
              <div className="p-8">
                <Empty title={d.items.length ? "Nothing matches these filters" : "No clusters in this period"} />
              </div>
            ) : (
              <MapContainer
                key={`${days}-${rows.map((c) => c.id).join()}`}
                center={[rows[0].centre_lat, rows[0].centre_lng]}
                zoom={13}
                scrollWheelZoom={false}
                style={{ height: 440 }}
                aria-label="Map of outbreak clusters"
              >
                <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                {rows.map((c) => (
                  <Circle
                    key={c.id}
                    center={[c.centre_lat, c.centre_lng]}
                    radius={c.radius_km * 1000}
                    eventHandlers={{ click: () => setOpenId(c.id) }}
                    pathOptions={{ color: colour(c), fillColor: colour(c), fillOpacity: c.current ? 0.25 : 0.1, weight: 2, dashArray: c.current ? undefined : "6 6" }}
                  >
                    <MapTooltip>
                      {SYNDROME[c.syndrome]} · {c.region} · {c.cases} people
                    </MapTooltip>
                  </Circle>
                ))}
              </MapContainer>
            )}
          </Card>

          <section aria-labelledby="signal-list">
            <h2 id="signal-list" className="mb-3 text-xl text-ink">Signals</h2>
            <div className="mb-4 grid gap-3 md:grid-cols-[3fr_2fr]">
              <SearchInput value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search area, locality or symptom" aria-label="Search signals" />
              <div className="grid grid-cols-2 gap-3">
                <select aria-label="When" value={days} onChange={(e) => setDays(Number(e.target.value))} className={cx(inputCls, "px-3")}>
                  {PERIODS.map((p) => (
                    <option key={p.days} value={p.days}>{p.label}</option>
                  ))}
                </select>
                <select aria-label="Severity" value={severity} onChange={(e) => setSeverity(e.target.value as typeof severity)} className={cx(inputCls, "px-3")}>
                  <option value="all">All severities</option>
                  <option value="outbreak">Possible outbreak</option>
                  <option value="watch">Watch</option>
                </select>
              </div>
            </div>

            {rows.length > 0 && (
              <Card className="overflow-x-auto p-0!">
                <table className="w-full min-w-[760px] text-left text-sm">
                  <thead className="text-xs font-semibold uppercase tracking-[0.06em] text-ink-soft">
                    <tr>
                      <th className="w-12 px-4 py-3 font-semibold">#</th>
                      <th className="px-4 py-3 font-semibold">Signal</th>
                      <th className="px-4 py-3 font-semibold">People</th>
                      <th className="px-4 py-3 font-semibold">Severity</th>
                      <th className="px-4 py-3 font-semibold">Status</th>
                      <th className="w-28 px-4 py-3"><span className="visually-hidden">View</span></th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((c, i) => (
                      <tr key={c.id} onClick={() => setOpenId(c.id)} className="cursor-pointer align-top hover:bg-paper">
                        <td className="px-4 py-3 tabular-nums text-ink-muted">{i + 1}</td>
                        <td className="px-4 py-3">
                          <span className="block font-semibold text-ink">
                            {SYNDROME[c.syndrome]} · {c.region}
                          </span>
                          <span className="block text-xs text-ink-soft">
                            {fmtDate(c.first_onset)} to {fmtDate(c.last_onset)}
                            {c.district ? ` · ${c.district}` : ""}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="font-semibold tabular-nums text-ink">{c.cases}</span>
                          <span className="block text-xs text-ink-soft">expected {c.expected.toFixed(1)}</span>
                        </td>
                        <td className="px-4 py-3"><SeverityPill c={c} /></td>
                        <td className="px-4 py-3"><StatusPills c={c} /></td>
                        <td className="px-4 py-3">
                          <button
                            type="button"
                            onClick={(ev) => {
                              ev.stopPropagation();
                              setOpenId(c.id);
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
          </section>
        </>
      )}
      {open && <Details cluster={open} onClose={() => setOpenId(null)} onChanged={res.reload} />}
    </>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-sm font-semibold text-ink">{label}</dt>
      <dd className="mt-0.5 text-sm text-ink-soft">{children}</dd>
    </div>
  );
}

function Details({ cluster: c, onClose, onChanged }: { cluster: Cluster; onClose: () => void; onChanged: () => void }) {
  const [verdict, setVerdict] = useState<Verdict | null>(c.feedback);
  const [note, setNote] = useState(c.feedback_note ?? "");
  const [busy, setBusy] = useState<"save" | "seen" | null>(null);
  const { notify } = useToast();
  const symptoms = Object.entries(c.symptoms);
  const draft = new URLSearchParams({
    cluster: c.id,
    title: `${SYNDROME[c.syndrome]} cases in ${c.region}`,
    body: `Several people in and around ${c.region} have reported ${symptoms.slice(0, 4).map(([s]) => s).join(", ") || "similar symptoms"} in the last few days. If you have these symptoms, rest, drink plenty of fluids, and see your health centre if they last more than two days.`,
  });

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const act = async (kind: "save" | "seen", fn: () => Promise<unknown>, done: string) => {
    setBusy(kind);
    try {
      await fn();
      notify({ tone: "success", title: done, body: `${SYNDROME[c.syndrome]} · ${c.region}` });
      onChanged();
    } catch (e) {
      notify({ tone: "alert", title: "Could not save", body: errorMessage(e) });
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-ink/40 p-4" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="cluster-title"
        onClick={(e) => e.stopPropagation()}
        className={cx("flex max-h-[calc(100dvh-2rem)] w-full max-w-4xl flex-col overflow-hidden rounded-3xl border-l-8 bg-surface shadow-lg", c.outbreak ? "border-l-red-600" : "border-l-amber-500")}
      >
        <header className="flex items-start justify-between gap-4 border-b border-line p-6">
          <div>
            <h2 id="cluster-title" className="text-2xl text-ink">
              {SYNDROME[c.syndrome]} · {c.region}
            </h2>
            <div className="mt-2 flex flex-wrap gap-2">
              <SeverityPill c={c} />
              {c.current ? <Pill className="bg-sky-50 text-sky-800">Active</Pill> : <Pill className="bg-paper-raised text-ink-soft">Ended</Pill>}
            </div>
          </div>
          <button type="button" onClick={onClose} className="grid h-10 w-10 shrink-0 place-items-center rounded-full text-ink-soft hover:bg-paper" aria-label="Close">
            <X size={20} aria-hidden="true" />
          </button>
        </header>

        <div className="grid gap-6 overflow-y-auto p-6 md:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
          <div className="flex flex-col gap-5">
            <div>
              <h3 className="mb-2 text-base font-bold text-ink">Why it was flagged</h3>
              <ol className="flex flex-col gap-2">
                {c.reasons.map((r, i) => (
                  <li key={i} className="flex gap-3 text-sm text-ink">
                    <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-paper text-xs font-semibold text-ink-soft">{i + 1}</span>
                    <span>{r}</span>
                  </li>
                ))}
              </ol>
            </div>
            <dl className="grid gap-4 sm:grid-cols-2">
              <Field label="Area">
                {Object.entries(c.localities).map(([l, n]) => `${l} (${n})`).join(", ") || c.region}
                {c.district ? ` · ${c.district}` : ""}
              </Field>
              <Field label="People reported">{c.cases} (expected {c.expected.toFixed(1)})</Field>
              <Field label="Onset">{fmtDate(c.first_onset)} to {fmtDate(c.last_onset)}</Field>
              <Field label="Spread">{c.radius_km.toFixed(1)} km radius</Field>
              <Field label="Chance it is random">p = {c.p_value.toFixed(4)}</Field>
              <Field label="Last seen by a check">{fmtDateTime(c.seen_at)}</Field>
            </dl>
            {symptoms.length > 0 && (
              <div>
                <h3 className="mb-2 text-sm font-semibold text-ink">Symptoms</h3>
                <div className="flex flex-wrap gap-2">
                  {symptoms.map(([s, n]) => (
                    <Pill key={s} className="bg-paper text-ink">{s} · {n}</Pill>
                  ))}
                </div>
              </div>
            )}
            <div className="flex flex-wrap items-center gap-2">
              {c.advisory_id ? (
                <span className="text-sm text-success">Advisory published</span>
              ) : (
                <Link to={`${paths.advisories}?${draft}`} className="inline-flex min-h-10 items-center gap-1.5 rounded-full border border-line px-4 text-sm font-semibold text-ink hover:bg-paper">
                  <Megaphone size={15} aria-hidden="true" /> Write an advisory
                </Link>
              )}
              {c.acknowledged_at ? (
                <span className="text-sm text-ink-soft">Seen by {c.acknowledged_by ?? "someone"} {fmtAgo(c.acknowledged_at)}</span>
              ) : (
                <Btn tone="ghost" busy={busy === "seen"} onClick={() => void act("seen", () => acknowledgeCluster(c.id), "Marked as seen")}>
                  Mark as seen
                </Btn>
              )}
            </div>
          </div>

          <div className="flex flex-col gap-4 md:border-l md:border-line md:pl-6">
            <h3 className="text-base font-bold text-ink">Was the clustering right?</h3>
            <p className="text-sm text-ink-soft">After checking on the ground, record whether this was a real outbreak. It tracks how accurate the signals are.</p>
            <div className="grid gap-2">
              {(Object.keys(VERDICT) as Verdict[]).map((k) => {
                const v = VERDICT[k];
                return (
                  <button
                    key={k}
                    type="button"
                    aria-pressed={verdict === k}
                    onClick={() => setVerdict(k)}
                    className={cx(
                      "flex min-h-11 items-center gap-2 rounded-xl border-2 px-3 text-sm font-semibold",
                      verdict === k ? "border-forest bg-matcha/20 text-ink" : "border-line text-ink-soft hover:border-ink/25",
                    )}
                  >
                    <v.icon size={16} aria-hidden="true" /> {v.label}
                  </button>
                );
              })}
            </div>
            <Labelled label="Notes" hint="What you found: confirmed cases, a common source, or why it was not an outbreak.">
              <textarea rows={4} maxLength={1000} value={note} onChange={(e) => setNote(e.target.value)} className={cx(inputCls, "py-3")} />
            </Labelled>
            {c.feedback_at && (
              <p className="text-xs text-ink-muted">
                Last reviewed {fmtDateTime(c.feedback_at)}
                {c.feedback_by ? ` by ${c.feedback_by}` : ""}
              </p>
            )}
            <div>
              <Btn tone="primary" busy={busy === "save"} disabled={!verdict} onClick={() => verdict && void act("save", () => reviewCluster(c.id, verdict, note), "Feedback saved")}>
                Save feedback
              </Btn>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
