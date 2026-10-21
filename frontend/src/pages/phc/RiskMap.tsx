import "leaflet/dist/leaflet.css";
import { CircleMarker, MapContainer, TileLayer, Tooltip as MapTooltip } from "react-leaflet";
import { workerState } from "../../components/app/phc";
import { Card, Empty, Loading, PageHeader, cx } from "../../components/app/ui";
import { useResource } from "../../lib/useResource";
import { getMap, type LocalityRisk } from "../../services/phc";

// Risk is an ordinal status, reusing the severity tokens. Always shown with its label.
const LEVEL: Record<LocalityRisk["level"], { label: string; color: string; text: string }> = {
  high: { label: "High", color: "rgb(var(--hn-sev-critical))", text: "text-sev-critical" },
  elevated: { label: "Elevated", color: "rgb(var(--hn-sev-high))", text: "text-sev-high" },
  some: { label: "Some", color: "rgb(var(--hn-sev-moderate))", text: "text-sev-moderate" },
  none: { label: "None", color: "rgb(var(--hn-success))", text: "text-success" },
};

/** Share of each locality's citizens with an open flag. Aggregate only: no names. */
export function RiskMap() {
  const map = useResource((s) => getMap(s), "map");
  const blocked = workerState(map);
  if (blocked) return blocked;
  const m = map.data;
  const placed = m?.items.filter((i): i is LocalityRisk & { lat: number; lng: number } => i.lat !== null && i.lng !== null) ?? [];
  const centre: [number, number] | null =
    m && m.facility_lat !== null && m.facility_lng !== null ? [m.facility_lat, m.facility_lng] : placed[0] ? [placed[0].lat, placed[0].lng] : null;

  return (
    <>
      <PageHeader title="Risk map" lead="Localities ranked by the share of their citizens with at least one open flag, right now." />
      {!m ? <Loading /> : m.items.length === 0 ? <Empty title="No localities to show" /> : (
        <div className="grid gap-6 lg:grid-cols-5">
          <Card className="overflow-hidden p-0 lg:col-span-3">
            {centre ? (
              <MapContainer center={centre} zoom={14} scrollWheelZoom={false} style={{ height: 420 }} aria-label="Map of locality risk">
                <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                {placed.map((i) => (
                  <CircleMarker
                    key={i.locality}
                    center={[i.lat, i.lng]}
                    radius={10 + Math.sqrt(i.citizens) * 3}
                    pathOptions={{ color: "rgb(var(--hn-surface))", weight: 2, fillColor: LEVEL[i.level].color, fillOpacity: 0.75 }}
                  >
                    <MapTooltip>
                      {i.locality}: {LEVEL[i.level].label} · {i.flagged} of {i.citizens} flagged
                    </MapTooltip>
                  </CircleMarker>
                ))}
              </MapContainer>
            ) : (
              <p className="p-5 text-sm text-ink-soft">No coordinates are recorded for this area; see the ranking.</p>
            )}
          </Card>
          <Card className="lg:col-span-2" title="Ranking" aside={<span className="text-xs text-ink-soft">Under {m.min_cell} citizens: grouped</span>}>
            <ol className="flex flex-col divide-y divide-line">
              {m.items.map((i, n) => (
                <li key={i.locality} className="flex items-center gap-3 py-2 text-sm">
                  <span className="w-5 text-right text-ink-soft tabular-nums">{n + 1}</span>
                  <span className="size-3 shrink-0 rounded-full" style={{ background: LEVEL[i.level].color }} aria-hidden="true" />
                  <span className="flex-1 text-ink">{i.locality}</span>
                  <span className={cx("text-xs font-semibold", LEVEL[i.level].text)}>{LEVEL[i.level].label}</span>
                  <span className="w-28 text-right tabular-nums text-ink-soft">
                    {Math.round(i.share * 100)}% ({i.flagged}/{i.citizens})
                  </span>
                </li>
              ))}
            </ol>
          </Card>
        </div>
      )}
    </>
  );
}
