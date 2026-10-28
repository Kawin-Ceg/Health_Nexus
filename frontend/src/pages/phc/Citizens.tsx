import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CalendarPlus, ClipboardList, Eye, Stethoscope } from "lucide-react";
import { workerState } from "../../components/app/phc";
import { ReportCitizen } from "../../components/app/ReportCitizen";
import { Btn, Card, Empty, Loading, PageHeader, SearchInput, SeverityBadge, cx, inputCls, Status, type StatusTone } from "../../components/app/ui";
import { Detail, Modal } from "../../components/app/visits";
import { fmtAgo, fmtStamp } from "../../lib/format";
import { intParam, oneOf, textParam, useQueryState } from "../../lib/params";
import { citizenRecordPath, examPath } from "../../lib/routes";
import { useResource } from "../../lib/useResource";
import { getDirectory, type DirectoryItem, type Engagement } from "../../services/phc";
import { VisitForm } from "./Schedule";

const STATUSES = ["attention", "never_logged", "silent", "ok"] as const;
const PAGE = 50;

const STATUS: Record<Engagement, { label: string; tone: StatusTone }> = {
  attention: { label: "Needs attention", tone: "danger" },
  never_logged: { label: "Never logged", tone: "progress" },
  silent: { label: "Gone quiet", tone: "warn" },
  ok: { label: "Logging", tone: "success" },
};

function StatusPill({ status }: { status: Engagement }) {
  return <Status tone={STATUS[status].tone}>{STATUS[status].label}</Status>;
}

export function Citizens() {
  const { params, set } = useQueryState();
  const status = oneOf(params.get("status"), STATUSES, null);
  const locality = textParam(params.get("locality"), 120);
  const offset = intParam(params.get("offset"), 0, 0, 100_000);
  const [search, setSearch] = useState(() => textParam(params.get("q"), 80));
  const [q, setQ] = useState(search);
  const [openId, setOpenId] = useState<string | null>(null);
  const [booking, setBooking] = useState<DirectoryItem | null>(null);
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
  const open = d?.items.find((c) => c.citizen.id === openId) ?? null;

  return (
    <>
      <PageHeader
        title="Citizens"
        lead={d ? `Everyone registered to your centre, ${d.catchment_total} in all. Sorted by what is worth opening first.` : undefined}
      />
      <div className="mb-5 grid gap-3 lg:grid-cols-[3fr_2fr]">
        <SearchInput value={search} maxLength={80} onChange={(e) => setSearch(e.target.value)} placeholder="Search name or HN- reference" aria-label="Search citizens" />
        <div className="grid grid-cols-2 gap-3">
          <select aria-label="Status" value={status ?? ""} onChange={(e) => set({ status: e.target.value || null, offset: null })} className={cx(inputCls, "px-3")}>
            <option value="">All statuses{d ? ` (${d.catchment_total})` : ""}</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>{STATUS[s].label}{d ? ` (${d.counts[s]})` : ""}</option>
            ))}
          </select>
          <select aria-label="Locality" value={locality} onChange={(e) => set({ locality: e.target.value, offset: null })} className={cx(inputCls, "px-3")}>
            <option value="">All localities</option>
            {d?.localities.map((l) => (
              <option key={l.locality} value={l.locality === "Unspecified" ? "" : l.locality} disabled={l.locality === "Unspecified"}>
                {l.locality} ({l.citizens})
              </option>
            ))}
          </select>
        </div>
      </div>

      {!d ? (
        <Loading />
      ) : d.items.length === 0 ? (
        <Empty title="No citizens match" />
      ) : (
        <Card className={cx("overflow-x-auto p-0!", dir.loading && "opacity-60")}>
          <table className="w-full min-w-[820px] text-left text-sm">
            <thead className="text-xs font-semibold uppercase tracking-[0.06em] text-ink-soft">
              <tr>
                <th className="w-12 px-4 py-3 font-semibold">#</th>
                <th className="px-4 py-3 font-semibold">Citizen</th>
                <th className="px-4 py-3 font-semibold">Status</th>
                <th className="px-4 py-3 font-semibold">Open flags</th>
                <th className="px-4 py-3 font-semibold">Last reading</th>
                <th className="px-4 py-3 font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {d.items.map((c, i) => (
                <tr key={c.citizen.id} onClick={() => setOpenId(c.citizen.id)} className="cursor-pointer align-top hover:bg-paper">
                  <td className="px-4 py-3 tabular-nums text-ink-muted">{offset + i + 1}</td>
                  <td className="px-4 py-3">
                    <span className="block font-semibold text-ink">{c.citizen.name}</span>
                    <span className="block text-xs text-ink-soft">
                      <span className="font-mono">{c.citizen.ref}</span>
                      {c.citizen.area ? ` · ${c.citizen.area}` : ""}
                    </span>
                  </td>
                  <td className="px-4 py-3"><StatusPill status={c.status} /></td>
                  <td className="px-4 py-3">
                    {c.open_flags > 0 && c.worst_severity ? (
                      <span className="flex items-center gap-2">
                        <SeverityBadge severity={c.worst_severity} /> {c.open_flags}
                      </span>
                    ) : (
                      <span className="text-ink-soft">—</span>
                    )}
                  </td>
                  <td className={cx("px-4 py-3", c.status === "silent" ? "text-amber-800" : "text-ink-soft")}>
                    {c.last_reading_at ? fmtAgo(c.last_reading_at) : "Never"}
                  </td>
                  <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                    <span className="flex flex-wrap gap-1">
                      <button type="button" onClick={() => setOpenId(c.citizen.id)} className="inline-flex min-h-9 items-center gap-1.5 rounded-lg px-2.5 text-sm font-medium text-blue-700 hover:bg-blue-50">
                        <Eye size={15} aria-hidden="true" /> View
                      </button>
                      <button type="button" onClick={() => setBooking(c)} className="inline-flex min-h-9 items-center gap-1.5 rounded-lg px-2.5 text-sm font-medium text-green-800 hover:bg-green-50">
                        <CalendarPlus size={15} aria-hidden="true" /> Book
                      </button>
                      <Link to={examPath(c.citizen.id)} className="inline-flex min-h-9 items-center gap-1.5 rounded-lg px-2.5 text-sm font-medium text-violet-800 hover:bg-violet-50">
                        <Stethoscope size={15} aria-hidden="true" /> Examine
                      </Link>
                    </span>
                  </td>
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
            <Btn disabled={offset === 0} onClick={() => set({ offset: Math.max(0, offset - PAGE) || null })}>Previous</Btn>
            <Btn disabled={offset + PAGE >= d.total} onClick={() => set({ offset: offset + PAGE })}>Next</Btn>
          </div>
        </nav>
      )}
      {d && <p className="mt-3 text-xs text-ink-soft">"Gone quiet": no reading in {d.silent_after_days} days.</p>}

      {open && !booking && <CitizenDetails item={open} onClose={() => setOpenId(null)} onBook={() => setBooking(open)} />}
      {booking && (
        <VisitForm
          preset={booking.citizen}
          onClose={() => setBooking(null)}
          onSaved={() => {
            setBooking(null);
            setOpenId(null);
            dir.reload();
          }}
        />
      )}
    </>
  );
}

function CitizenDetails({ item: c, onClose, onBook }: { item: DirectoryItem; onClose: () => void; onBook: () => void }) {
  const [reporting, setReporting] = useState(false);
  const p = c.citizen;
  return (
    <Modal title={p.name} onClose={onClose} wide>
      <div className="flex flex-col gap-5">
        <div className="flex flex-wrap items-center gap-2">
          <StatusPill status={c.status} />
          {c.worst_severity && c.open_flags > 0 && <SeverityBadge severity={c.worst_severity} />}
        </div>
        <dl className="grid gap-4 sm:grid-cols-3">
          <Detail label="Reference">{p.ref}</Detail>
          <Detail label="Locality">{p.area ?? "—"}</Detail>
          <Detail label="Phone">{p.phone ? <a href={`tel:${p.phone.replace(/[^\d+]/g, "")}`} className="underline underline-offset-4">{p.phone}</a> : "—"}</Detail>
          <Detail label="Age and gender">{[c.age && `${c.age} yrs`, c.gender?.replace(/_/g, " ")].filter(Boolean).join(", ") || "—"}</Detail>
          <Detail label="Open flags">{c.open_flags}</Detail>
          <Detail label="Readings">{c.readings}</Detail>
          <Detail label="Last reading">{c.last_reading_at ? fmtStamp(c.last_reading_at) : "Never"}</Detail>
          <Detail label="Joined">{fmtStamp(c.joined_at)}</Detail>
        </dl>
        {reporting ? (
          <ReportCitizen citizenId={p.id} name={p.name} onClose={() => setReporting(false)} />
        ) : (
          <div className="flex flex-wrap gap-3">
            <Btn tone="primary" onClick={onBook}>
              <CalendarPlus size={16} aria-hidden="true" /> Book visit
            </Btn>
            <Link to={examPath(p.id)} className="inline-flex min-h-11 items-center gap-2 rounded-full border border-line px-5 font-semibold text-ink hover:bg-paper">
              <Stethoscope size={16} aria-hidden="true" /> Record examination
            </Link>
            <Link to={citizenRecordPath(p.id)} className="inline-flex min-h-11 items-center gap-2 rounded-full border border-line px-5 font-semibold text-ink hover:bg-paper">
              <ClipboardList size={16} aria-hidden="true" /> Full record
            </Link>
            <Btn tone="ghost" onClick={() => setReporting(true)}>Report a problem</Btn>
          </div>
        )}
      </div>
    </Modal>
  );
}
