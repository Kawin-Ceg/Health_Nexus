import { useMemo, useState } from "react";
import { Bell, CalendarClock, Clock, Eye, FileWarning, MapPin, Megaphone, Watch } from "lucide-react";
import { Detail, Modal } from "../../components/app/visits";
import { Btn, Card, Empty, ErrorNote, Loading, PageHeader, SearchInput, cx, inputCls } from "../../components/app/ui";
import { useAuth } from "../../context/AuthContext";
import { useT } from "../../i18n";
import { fmtDate, fmtDateTime } from "../../lib/format";
import { play } from "../../lib/sound";
import { useResource } from "../../lib/useResource";
import type { Advisory } from "../../services/advisories";
import { getAlerts, markRead, type AlertItem } from "../../services/health";

const LEVEL: Record<AlertItem["severity"], { label: string; cls: string; bar: string }> = {
  high: { label: "Important", cls: "bg-red-100 text-red-900", bar: "border-l-red-600" },
  medium: { label: "Take note", cls: "bg-amber-100 text-amber-900", bar: "border-l-amber-500" },
  low: { label: "For information", cls: "bg-green-100 text-green-900", bar: "border-l-green-600" },
};

const ADVISORY: Record<Advisory["severity"], { label: string; cls: string }> = {
  high: { label: "Red", cls: "bg-red-100 text-red-900" },
  medium: { label: "Yellow", cls: "bg-amber-100 text-amber-900" },
  low: { label: "Green", cls: "bg-green-100 text-green-900" },
};

const PERIODS = [
  { days: 0, label: "Any time" },
  { days: 1, label: "Last 24 hours" },
  { days: 7, label: "Last 7 days" },
  { days: 30, label: "Last 30 days" },
  { days: 90, label: "Last 3 months" },
];

/** The main topic of an alert, read from its wording. */
function topic(a: AlertItem): { title: string; icon: typeof Bell } {
  const m = a.message.toLowerCase();
  if (a.alert_type === "community") return { title: "Community notice", icon: Megaphone };
  if (m.includes("visit")) {
    if (m.includes("cancel")) return { title: "Visit cancelled", icon: CalendarClock };
    if (m.includes("moved")) return { title: "Visit moved", icon: CalendarClock };
    if (m.includes("no outcome") || m.includes("missed")) return { title: "Visit missed", icon: CalendarClock };
    return { title: "Visit booked", icon: CalendarClock };
  }
  if (m.includes("watch") || m.includes("sync")) return { title: "Smartwatch", icon: Watch };
  if (m.includes("flag") || m.includes("reading") || m.includes("unusual")) return { title: "Reading flagged", icon: FileWarning };
  return { title: "Notice", icon: Bell };
}

function advisoryState(a: Advisory) {
  return a.withdrawn_at ? ["Withdrawn", "bg-paper-raised text-ink-soft"] : a.active ? ["Running", "bg-sky-100 text-sky-900"] : ["Ended", "bg-paper-raised text-ink-soft"];
}

export function CitizenAlerts() {
  const t = useT();
  const { user } = useAuth();
  const res = useResource((s) => getAlerts(s), "alerts");
  const [tab, setTab] = useState<"alerts" | "advisories">("alerts");
  const [search, setSearch] = useState("");
  const [level, setLevel] = useState("");
  const [days, setDays] = useState(0);
  const [seen, setSeen] = useState<"" | "new" | "seen">("");
  const [opened, setOpened] = useState<Set<string>>(new Set());
  const [openAlert, setOpenAlert] = useState<AlertItem | null>(null);
  const [openAdvisory, setOpenAdvisory] = useState<Advisory | null>(null);

  const d = res.data;
  const area = user?.district ?? "Your area";
  const read = (a: AlertItem) => a.is_read || opened.has(a.id);
  const since = days ? Date.now() - days * 86400_000 : 0;
  const q = search.trim().toLowerCase();

  const alerts = useMemo(
    () =>
      (d?.alerts ?? []).filter(
        (a) =>
          (!level || a.severity === level) &&
          new Date(a.created_at).getTime() >= since &&
          (!seen || (seen === "seen") === (a.is_read || opened.has(a.id))) &&
          (!q || `${topic(a).title} ${a.message}`.toLowerCase().includes(q)),
      ),
    [d, level, since, seen, opened, q],
  );
  const advisories = useMemo(
    () =>
      (d?.advisories ?? []).filter(
        (a) => (!level || a.severity === level) && new Date(a.created_at).getTime() >= since && (!q || `${a.title} ${a.body}`.toLowerCase().includes(q)),
      ),
    [d, level, since, q],
  );
  const unread = (d?.alerts ?? []).filter((a) => !read(a));

  // Opening an alert marks it as seen, so "Seen" means the citizen actually looked at it.
  const open = (a: AlertItem) => {
    setOpenAlert(a);
    if (!read(a)) {
      setOpened((s) => new Set(s).add(a.id));
      void markRead([a.id]).catch(() => undefined);
    }
  };
  const markAll = () => {
    const ids = unread.map((a) => a.id);
    setOpened((s) => new Set([...s, ...ids]));
    void markRead(ids).then(() => play("clear")).catch(() => undefined);
  };

  return (
    <>
      <PageHeader title={t("alerts.title")} lead="Notices about your readings and visits, and health advisories for your area." />
      <div role="tablist" aria-label="Show" className="mb-4 inline-flex rounded-full border border-line bg-surface p-1">
        {(
          [
            ["alerts", "Your alerts", d?.alerts.length],
            ["advisories", "Advisories", d?.advisories.length],
          ] as const
        ).map(([id, label, n]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            onClick={() => {
              setTab(id);
              setLevel("");
            }}
            className={cx("min-h-10 rounded-full px-5 text-sm font-semibold transition-colors", tab === id ? "bg-ink text-paper" : "text-ink-soft hover:text-ink")}
          >
            {label} {n != null && <span className="tabular-nums opacity-70">{n}</span>}
          </button>
        ))}
      </div>

      <div className="mb-5 grid gap-3 md:grid-cols-[3fr_2fr]">
        <SearchInput value={search} onChange={(e) => setSearch(e.target.value)} placeholder={tab === "alerts" ? "Search alerts" : "Search advisories"} aria-label="Search" />
        <div className={cx("grid gap-3", tab === "alerts" ? "grid-cols-3" : "grid-cols-2")}>
          <select aria-label="Importance" value={level} onChange={(e) => setLevel(e.target.value)} className={cx(inputCls, "px-3")}>
            <option value="">All levels</option>
            {Object.entries(tab === "alerts" ? LEVEL : ADVISORY).map(([k, v]) => (
              <option key={k} value={k}>{v.label}</option>
            ))}
          </select>
          <select aria-label="When" value={days} onChange={(e) => setDays(Number(e.target.value))} className={cx(inputCls, "px-3")}>
            {PERIODS.map((p) => (
              <option key={p.days} value={p.days}>{p.label}</option>
            ))}
          </select>
          {tab === "alerts" && (
            <select aria-label="Seen" value={seen} onChange={(e) => setSeen(e.target.value as typeof seen)} className={cx(inputCls, "px-3")}>
              <option value="">Seen and new</option>
              <option value="new">New only</option>
              <option value="seen">Seen only</option>
            </select>
          )}
        </div>
      </div>

      {res.error && <ErrorNote message={res.error} onRetry={res.reload} />}
      {!d ? (
        !res.error && <Loading />
      ) : tab === "alerts" ? (
        <>
          {unread.length > 0 && (
            <div className="mb-4 flex items-center justify-between gap-3">
              <p className="text-sm text-ink-soft">{unread.length} new alert{unread.length === 1 ? "" : "s"}</p>
              <Btn tone="ghost" onClick={markAll}>Mark all as seen</Btn>
            </div>
          )}
          {alerts.length === 0 ? (
            <Empty title={d.alerts.length ? "Nothing matches these filters" : "No alerts yet"} />
          ) : (
            <ul className="grid gap-5 md:grid-cols-2 2xl:grid-cols-3">
              {alerts.map((a) => {
                const tp = topic(a);
                const isRead = read(a);
                return (
                  <li key={a.id}>
                    <button
                      type="button"
                      onClick={() => open(a)}
                      className={cx(
                        "flex h-full w-full flex-col gap-4 rounded-lg border border-l-4 border-line bg-surface p-5 text-left text-sm transition-colors hover:border-ink/40 focus-visible:outline-2 focus-visible:outline-ink",
                        LEVEL[a.severity].bar,
                      )}
                    >
                      <span className="flex items-start gap-3">
                        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-matcha/25 text-forest" aria-hidden="true">
                          <tp.icon size={18} />
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block text-base font-semibold leading-snug text-ink">{tp.title}</span>
                          <span className="mt-0.5 line-clamp-1 block text-ink-muted">{a.message}</span>
                        </span>
                        <span className={cx("shrink-0 rounded-full px-3 py-1 text-xs font-semibold", LEVEL[a.severity].cls)}>{LEVEL[a.severity].label}</span>
                      </span>
                      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2">
                        <dt className="flex items-center gap-1.5 text-ink-muted"><Clock size={14} aria-hidden="true" /> When</dt>
                        <dd className="text-ink">{fmtDateTime(a.created_at)}</dd>
                        <dt className="flex items-center gap-1.5 text-ink-muted"><MapPin size={14} aria-hidden="true" /> Area</dt>
                        <dd className="text-ink">{a.alert_type === "community" ? `${area} community` : area}</dd>
                      </dl>
                      <span className="mt-auto flex items-center justify-between border-t border-line pt-4">
                        <span className="text-xs text-ink-muted">Status</span>
                        <span className={cx("rounded-full px-3 py-1 text-xs font-semibold", isRead ? "bg-green-100 text-green-900" : "bg-ink text-paper")}>
                          {isRead ? "Seen" : "New, not seen yet"}
                        </span>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </>
      ) : advisories.length === 0 ? (
        <Empty title={d.advisories.length ? "Nothing matches these filters" : "No advisories for your area right now"} />
      ) : (
        <Card className="overflow-x-auto p-0!">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="text-xs font-semibold uppercase tracking-[0.06em] text-ink-soft">
              <tr>
                <th className="w-12 px-4 py-3 font-semibold">#</th>
                <th className="px-4 py-3 font-semibold">Title</th>
                <th className="px-4 py-3 font-semibold">Status</th>
                <th className="px-4 py-3 font-semibold">Severity</th>
                <th className="w-28 px-4 py-3"><span className="visually-hidden">View</span></th>
              </tr>
            </thead>
            <tbody>
              {advisories.map((a, i) => {
                const [label, cls] = advisoryState(a);
                return (
                  <tr key={a.id} onClick={() => setOpenAdvisory(a)} className="cursor-pointer align-top hover:bg-paper">
                    <td className="px-4 py-3 tabular-nums text-ink-muted">{i + 1}</td>
                    <td className="px-4 py-3">
                      <span className="block font-semibold text-ink">{a.title}</span>
                      <span className="block text-xs text-ink-soft">{a.audience} · {fmtDateTime(a.created_at)}</span>
                    </td>
                    <td className="px-4 py-3"><span className={cx("inline-block rounded-full px-3 py-1 text-xs font-semibold", cls)}>{label}</span></td>
                    <td className="px-4 py-3"><span className={cx("inline-block rounded-full px-3 py-1 text-xs font-semibold", ADVISORY[a.severity].cls)}>{ADVISORY[a.severity].label}</span></td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        onClick={(ev) => {
                          ev.stopPropagation();
                          setOpenAdvisory(a);
                        }}
                        className="inline-flex min-h-9 items-center gap-1.5 rounded-lg px-2.5 text-sm font-medium text-blue-700 hover:bg-blue-50 focus-visible:outline-2 focus-visible:outline-blue-700"
                      >
                        <Eye size={15} aria-hidden="true" /> View
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Card>
      )}

      {openAlert && (
        <Modal title={topic(openAlert).title} onClose={() => setOpenAlert(null)}>
          <div className="flex flex-col gap-5">
            <div className="flex flex-wrap gap-2">
              <span className={cx("rounded-full px-3 py-1 text-xs font-semibold", LEVEL[openAlert.severity].cls)}>{LEVEL[openAlert.severity].label}</span>
              <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-semibold text-green-900">Seen</span>
            </div>
            <div>
              <h3 className="mb-1 text-base font-bold text-ink">Message</h3>
              <p className="whitespace-pre-line text-base text-ink">{openAlert.message}</p>
            </div>
            <dl className="grid gap-4 sm:grid-cols-2">
              <Detail label="Received">{fmtDateTime(openAlert.created_at)}</Detail>
              <Detail label="Area">{area}</Detail>
              <Detail label="Kind">{openAlert.alert_type === "community" ? "Community notice" : "About you"}</Detail>
              <Detail label="Importance">{LEVEL[openAlert.severity].label}</Detail>
            </dl>
          </div>
        </Modal>
      )}
      {openAdvisory && (
        <Modal title={openAdvisory.title} onClose={() => setOpenAdvisory(null)} wide>
          <div className="flex flex-col gap-5">
            <div className="flex flex-wrap gap-2">
              <span className={cx("rounded-full px-3 py-1 text-xs font-semibold", ADVISORY[openAdvisory.severity].cls)}>{ADVISORY[openAdvisory.severity].label}</span>
              <span className={cx("rounded-full px-3 py-1 text-xs font-semibold", advisoryState(openAdvisory)[1])}>{advisoryState(openAdvisory)[0]}</span>
            </div>
            <div>
              <h3 className="mb-1 text-base font-bold text-ink">Message</h3>
              <p className="whitespace-pre-line text-base text-ink">{openAdvisory.body}</p>
            </div>
            <dl className="grid gap-4 sm:grid-cols-2">
              <Detail label="Released">{fmtDateTime(openAdvisory.created_at)}</Detail>
              <Detail label={openAdvisory.withdrawn_at ? "Withdrawn" : openAdvisory.active ? "Runs until" : "Ended"}>
                {fmtDate(openAdvisory.withdrawn_at ?? openAdvisory.expires_at)}
              </Detail>
              <Detail label="For">{openAdvisory.audience}</Detail>
              <Detail label="Published by">{openAdvisory.author ?? "Your health authority"}</Detail>
            </dl>
          </div>
        </Modal>
      )}
    </>
  );
}
