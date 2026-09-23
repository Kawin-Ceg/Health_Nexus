import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  Bell,
  CalendarDays,
  ClipboardList,
  HeartPulse,
  History,
  LayoutDashboard,
  LogOut,
  Map,
  Menu,
  PlusCircle,
  Settings,
  UserRound,
  Users,
  BarChart3,
  X,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { paths } from "../../lib/routes";
import { setTheme } from "../../lib/theme";
import { getPreferences } from "../../services/account";
import { getUnreadCount } from "../../services/health";
import { getPhcBadge } from "../../services/phc";
import { Logo } from "../ui/Logo/Logo";
import { cx } from "./ui";

const BADGE_POLL_MS = 60_000;

interface Item {
  to: string;
  label: string;
  icon: typeof Bell;
  badge?: number;
  end?: boolean;
}

function useBadges(role: string | undefined) {
  const [citizenUnread, setCitizenUnread] = useState(0);
  const [phc, setPhc] = useState({ unread: 0, citizens_flagged: 0 });
  const location = useLocation();

  useEffect(() => {
    if (!role) return;
    const controller = new AbortController();
    const load = () => {
      if (role === "user") getUnreadCount(controller.signal).then(setCitizenUnread).catch(() => undefined);
      if (role === "phc_worker") getPhcBadge(controller.signal).then(setPhc).catch(() => undefined);
    };
    load();
    const timer = window.setInterval(load, BADGE_POLL_MS);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
    // Re-read on navigation: reading the alerts page clears the badge.
  }, [role, location.pathname]);
  return { citizenUnread, phc };
}

/** The signed-in layout for citizens and PHC workers: navigation, badges, theme. */
export function AppShell() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const { citizenUnread, phc } = useBadges(user?.role);

  useEffect(() => {
    getPreferences()
      .then((p) => setTheme(p.theme))
      .catch(() => undefined);
  }, []);
  useEffect(() => setOpen(false), [location.pathname]);

  const items: Item[] =
    user?.role === "phc_worker"
      ? [
          { to: paths.phcHome, label: "Dashboard", icon: LayoutDashboard, end: true },
          { to: paths.phcAlerts, label: "Alerts", icon: Bell, badge: phc.citizens_flagged },
          { to: paths.phcCitizens, label: "Citizens", icon: Users },
          { to: paths.phcSchedule, label: "Schedule", icon: CalendarDays },
          { to: paths.phcReports, label: "Reports", icon: BarChart3 },
          { to: paths.phcMap, label: "Risk map", icon: Map },
          { to: paths.notifications, label: "Notifications", icon: ClipboardList, badge: phc.unread },
        ]
      : [
          { to: paths.citizenHome, label: "Dashboard", icon: LayoutDashboard, end: true },
          { to: paths.submitVitals, label: "Log vitals", icon: PlusCircle },
          { to: paths.history, label: "History", icon: History },
          { to: paths.citizenAlerts, label: "Alerts & visits", icon: Bell, badge: citizenUnread },
        ];
  const account: Item[] = [
    { to: paths.profile, label: "Profile", icon: UserRound },
    { to: paths.settings, label: "Settings", icon: Settings },
  ];

  const link = (item: Item) => (
    <NavLink
      key={item.to}
      to={item.to}
      end={item.end}
      className={({ isActive }) =>
        cx(
          "flex min-h-10 items-center gap-3 rounded-xl px-3 text-sm font-medium",
          isActive ? "bg-brand-soft text-brand" : "text-ink-soft hover:bg-paper-raised hover:text-ink",
        )
      }
    >
      <item.icon size={18} aria-hidden="true" />
      <span className="flex-1">{item.label}</span>
      {!!item.badge && (
        <span className="rounded-full bg-danger px-2 py-0.5 text-xs font-semibold text-white" aria-label={`${item.badge} new`}>
          {item.badge > 99 ? "99+" : item.badge}
        </span>
      )}
    </NavLink>
  );

  return (
    <div className="min-h-dvh bg-paper lg:grid lg:grid-cols-[240px_1fr]">
      <header className="sticky top-0 z-40 flex items-center justify-between border-b border-line bg-surface px-4 py-2 lg:hidden">
        <Logo />
        <button
          type="button"
          className="rounded-lg p-2 text-ink"
          aria-expanded={open}
          aria-controls="app-nav"
          onClick={() => setOpen((o) => !o)}
        >
          {open ? <X size={22} aria-hidden="true" /> : <Menu size={22} aria-hidden="true" />}
          <span className="visually-hidden">Menu</span>
        </button>
      </header>
      <aside
        id="app-nav"
        className={cx(
          "border-r border-line bg-surface p-4 lg:sticky lg:top-0 lg:flex lg:h-dvh lg:flex-col",
          open ? "flex flex-col" : "hidden",
        )}
      >
        <div className="mb-6 hidden lg:block">
          <Logo />
        </div>
        <nav aria-label="Main" className="flex flex-col gap-1">
          {items.map(link)}
        </nav>
        <div className="mt-6 border-t border-line pt-4 lg:mt-auto">
          <nav aria-label="Account" className="flex flex-col gap-1">
            {account.map(link)}
            <button
              type="button"
              onClick={() => void logout()}
              className="flex min-h-10 items-center gap-3 rounded-xl px-3 text-sm font-medium text-ink-soft hover:bg-paper-raised hover:text-ink"
            >
              <LogOut size={18} aria-hidden="true" />
              Sign out
            </button>
          </nav>
          {user && (
            <p className="mt-3 flex items-center gap-2 px-3 text-xs text-ink-soft">
              <HeartPulse size={14} aria-hidden="true" />
              <span className="truncate">{user.name}</span>
            </p>
          )}
        </div>
      </aside>
      <main className="mx-auto w-full max-w-6xl px-4 py-6 md:px-8 md:py-8">
        <Outlet />
      </main>
    </div>
  );
}
