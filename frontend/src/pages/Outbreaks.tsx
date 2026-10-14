import "leaflet/dist/leaflet.css";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Circle, MapContainer, TileLayer, Tooltip as MapTooltip } from "react-leaflet";
import { Megaphone, RefreshCw } from "lucide-react";
import { Btn, Card, Empty, ErrorNote, Loading, PageHeader, cx } from "../components/app/ui";
import { useToast } from "../components/app/Toaster";
import { useAuth } from "../context/AuthContext";
import { fmtAgo, fmtDate } from "../lib/format";
import { paths } from "../lib/routes";
import { useResource } from "../lib/useResource";
import { errorMessage } from "../services/api";
import { acknowledgeCluster, getClusters, runClustering, type Cluster } from "../services/outbreaks";

const SYNDROME: Record<Cluster["syndrome"], string> = {
  febrile: "Fever",
  respiratory: "Respiratory",
  gastrointestinal: "Stomach and gut",
};

const colour = (c: Cluster) => (c.outbreak ? "rgb(var(--hn-sev-critical))" : "rgb(var(--hn-sev-moderate))");

export function Outbreaks() {
  const { user } = useAuth();
  const admin = user?.role === "admin";
  const res = useResource((s) => getClusters(s), "clusters");
  const [running, setRunning] = useState(false);
  const { notify } = useToast();
  const d = res.data;

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
          {d.items.length === 0 ? (
            <Empty title="No clusters right now" />
          ) : (
            <div className="grid gap-6 lg:grid-cols-5">
              <Card className="overflow-hidden p-0 lg:col-span-3">
                <MapContainer
                  center={[d.items[0].centre_lat, d.items[0].centre_lng]}
                  zoom={13}
                  scrollWheelZoom={false}
                  style={{ height: 460 }}
                  aria-label="Map of outbreak clusters"
                >
                  <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                  {d.items.map((c) => (
                    <Circle
                      key={c.id}
                      center={[c.centre_lat, c.centre_lng]}
                      radius={c.radius_km * 1000}
                      pathOptions={{ color: colour(c), fillColor: colour(c), fillOpacity: 0.25, weight: 2 }}
                    >
                      <MapTooltip>
                        {SYNDROME[c.syndrome]} · {c.region} · {c.cases} people
                      </MapTooltip>
                    </Circle>
                  ))}
                </MapContainer>
              </Card>
              <ul className="flex flex-col gap-3 lg:col-span-2">
                {d.items.map((c) => (
                  <ClusterCard key={c.id} cluster={c} windowDays={d.window_days} onChanged={res.reload} />
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </>
  );
}

function ClusterCard({ cluster: c, windowDays, onChanged }: { cluster: Cluster; windowDays: number; onChanged: () => void }) {
  const [busy, setBusy] = useState(false);
  const { notify } = useToast();
  const symptoms = Object.entries(c.symptoms).slice(0, 4);
  const draft = new URLSearchParams({
    cluster: c.id,
    title: `${SYNDROME[c.syndrome]} cases in ${c.region}`,
    body: `Several people in and around ${c.region} have reported ${symptoms.map(([s]) => s).join(", ") || "similar symptoms"} in the last few days. If you have these symptoms, rest, drink plenty of fluids, and see your health centre if they last more than two days.`,
  });

  const acknowledge = async () => {
    setBusy(true);
    try {
      await acknowledgeCluster(c.id);
      onChanged();
    } catch (e) {
      notify({ tone: "alert", title: "Could not acknowledge", body: errorMessage(e) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <li className={cx("rounded-2xl border border-l-4 bg-surface p-4 text-sm", c.outbreak ? "border-line border-l-sev-critical" : "border-line border-l-sev-moderate")}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="font-semibold text-ink">
          {SYNDROME[c.syndrome]} · {c.region}
        </p>
        <span className={cx("rounded-full px-2 py-0.5 text-xs font-semibold", c.outbreak ? "bg-sev-critical/15 text-sev-critical" : "bg-sev-moderate/15 text-sev-moderate")}>
          {c.outbreak ? "Possible outbreak" : "Watch"}
        </span>
      </div>
      <p className="mt-1 text-ink">
        {c.cases} people within {c.radius_km.toFixed(1)} km, {fmtDate(c.first_onset)} to {fmtDate(c.last_onset)}. The area usually sees
        about {c.expected.toFixed(1)} in {windowDays} days
        {c.outbreak ? `, so this many is unlikely to be chance (p = ${c.p_value.toFixed(4)}).` : "."}
      </p>
      {symptoms.length > 0 && (
        <p className="mt-1 text-xs text-ink-soft">{symptoms.map(([s, n]) => `${s} ${n}`).join(" · ")}</p>
      )}
      <p className="mt-1 text-xs text-ink-soft">
        {Object.keys(c.localities).join(", ")}
        {c.district && ` · ${c.district}`} · {Math.round(c.prevalence * 100)}% of consenting residents nearby
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {c.advisory_id ? (
          <span className="text-xs text-success">Advisory published</span>
        ) : (
          <Link to={`${paths.advisories}?${draft}`} className="inline-flex min-h-9 items-center gap-1 rounded-full border border-line px-3 text-xs font-semibold text-ink hover:bg-paper">
            <Megaphone size={14} aria-hidden="true" /> Write an advisory
          </Link>
        )}
        {c.acknowledged_at ? (
          <span className="text-xs text-ink-soft">Seen by {c.acknowledged_by ?? "someone"} {fmtAgo(c.acknowledged_at)}</span>
        ) : (
          <Btn tone="ghost" busy={busy} onClick={() => void acknowledge()}>Mark as seen</Btn>
        )}
      </div>
    </li>
  );
}
