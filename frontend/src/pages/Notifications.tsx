import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Bell, CalendarCheck, CalendarClock, CalendarX, Check, CheckCheck, ChevronRight, ClipboardCheck, Megaphone, type LucideIcon } from "lucide-react";
import { Chips } from "../components/app/charts";
import { Btn, Card, Empty, ErrorNote, Loading, PageHeader, cx } from "../components/app/ui";
import { refreshBadges } from "../lib/badges";
import { fmtAgo, fmtDateTime } from "../lib/format";
import { paths } from "../lib/routes";
import { useResource } from "../lib/useResource";
import { getAlerts, markRead, type AlertItem } from "../services/health";

interface Kind {
  label: string;
  icon: LucideIcon;
  tint: string;
  action?: { label: string; to: string };
}

const KINDS: { test: RegExp; kind: Kind }[] = [
  {
    test: /needs an outcome|no outcome/i,
    kind: { label: "Needs an outcome", icon: ClipboardCheck, tint: "bg-yellow-50 text-yellow-700", action: { label: "Record outcome", to: `${paths.phcSchedule}?tab=outcome` } },
  },
  { test: /cancel/i, kind: { label: "Cancelled", icon: CalendarX, tint: "bg-red-50 text-red-700", action: { label: "Open schedule", to: `${paths.phcSchedule}?tab=cancelled` } } },
  { test: /moved|rescheduled/i, kind: { label: "Moved", icon: CalendarClock, tint: "bg-blue-50 text-blue-700", action: { label: "Open schedule", to: `${paths.phcSchedule}?tab=upcoming` } } },
  { test: /booked|will visit/i, kind: { label: "Booked", icon: CalendarCheck, tint: "bg-green-50 text-green-700", action: { label: "Open schedule", to: `${paths.phcSchedule}?tab=upcoming` } } },
  { test: /advisory|outbreak/i, kind: { label: "Notice", icon: Megaphone, tint: "bg-violet-50 text-violet-700" } },
];
const OTHER: Kind = { label: "Update", icon: Bell, tint: "bg-paper-raised text-ink-soft" };
const kindOf = (a: AlertItem) => KINDS.find((k) => k.test.test(a.message))?.kind ?? OTHER;

type Filter = "all" | "unread";

export function Notifications() {
  const { data, error, reload } = useResource((signal) => getAlerts(signal), "notifications");
  const [items, setItems] = useState<AlertItem[]>([]);
  const [filter, setFilter] = useState<Filter>("all");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (data) setItems(data.alerts);
  }, [data]);

  const unread = items.filter((a) => !a.is_read).length;
  const shown = useMemo(() => (filter === "unread" ? items.filter((a) => !a.is_read) : items), [items, filter]);

  const read = async (ids?: string[]) => {
    setItems((all) => all.map((a) => (!ids || ids.includes(a.id) ? { ...a, is_read: true } : a)));
    try {
      await markRead(ids);
    } catch {
      reload();
    }
    refreshBadges();
  };

  if (error) return <ErrorNote message={error} onRetry={reload} />;
  if (!data) return <Loading />;

  return (
    <>
      <PageHeader
        title="Notifications"
        actions={
          unread > 0 && (
            <Btn
              busy={busy}
              onClick={async () => {
                setBusy(true);
                await read();
                setBusy(false);
              }}
            >
              <CheckCheck size={16} aria-hidden="true" /> Mark all as read
            </Btn>
          )
        }
      />
      <div className="mb-4">
        <Chips
          label="Show"
          value={filter}
          onChange={setFilter}
          options={[
            { id: "all", label: `All (${items.length})` },
            { id: "unread", label: `Unread (${unread})` },
          ]}
        />
      </div>
      <Card className="p-0!">
        {shown.length === 0 ? (
          <div className="p-6">
            <Empty title={filter === "unread" ? "You're all caught up" : "No notifications yet"} />
          </div>
        ) : (
          <ul className="divide-y divide-line">
            {shown.map((a) => {
              const k = kindOf(a);
              return (
                <li key={a.id} className={cx("flex flex-wrap items-start gap-4 px-5 py-4 md:px-6", !a.is_read && "bg-blue-50/40")}>
                  <span className={cx("flex h-10 w-10 shrink-0 items-center justify-center rounded-full", k.tint)}>
                    <k.icon size={18} aria-hidden="true" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="flex flex-wrap items-center gap-2 text-xs text-ink-soft">
                      <span className="font-semibold text-ink-soft">{k.label}</span>
                      <span aria-hidden="true">·</span>
                      <time dateTime={a.created_at} title={fmtDateTime(a.created_at)}>{fmtAgo(a.created_at)}</time>
                      {!a.is_read && (
                        <span className="inline-flex items-center gap-1 font-semibold text-blue-700">
                          <span className="h-2 w-2 rounded-full bg-blue-600" aria-hidden="true" /> New
                        </span>
                      )}
                    </p>
                    <p className={cx("mt-1 text-sm text-ink", !a.is_read && "font-semibold")}>{a.message}</p>
                  </div>
                  <div className="flex shrink-0 flex-wrap items-center gap-1">
                    {k.action && (
                      <Link
                        to={k.action.to}
                        onClick={() => !a.is_read && void read([a.id])}
                        className="inline-flex min-h-9 items-center gap-1 rounded-lg px-2.5 text-sm font-semibold text-blue-700 hover:bg-blue-50"
                      >
                        {k.action.label} <ChevronRight size={15} aria-hidden="true" />
                      </Link>
                    )}
                    {!a.is_read && (
                      <button
                        type="button"
                        onClick={() => void read([a.id])}
                        className="inline-flex min-h-9 items-center gap-1 rounded-lg px-2.5 text-sm font-medium text-ink-soft hover:bg-paper-raised hover:text-ink"
                      >
                        <Check size={15} aria-hidden="true" /> Mark as read
                      </button>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </Card>
    </>
  );
}
