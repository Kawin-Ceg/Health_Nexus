import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  Activity,
  BadgeCheck,
  BarChart3,
  Building2,
  Bell,
  Sparkles,
  CalendarDays,
  ClipboardList,
  History,
  LayoutDashboard,
  LifeBuoy,
  LogOut,
  Map,
  Megaphone,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  ScrollText,
  Settings,
  UserRound,
  Users,
  Volume2,
  Watch,
  VolumeX,
  X,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { paths } from "../../lib/routes";
import { setSoundEnabled, soundEnabled } from "../../lib/sound";
import { setLanguage, useT } from "../../i18n";
import { setTheme } from "../../lib/theme";
import { getPreferences } from "../../services/account";
import { getOverview } from "../../services/admin";
import type { Role } from "../../services/auth";
import { getUnreadCount } from "../../services/health";
import { getPhcBadge } from "../../services/phc";
import { Doodle } from "../landing/Doodle/Doodle";
import { Logo } from "../ui/Logo/Logo";
import { LanguageSwitch } from "../ui/LanguageSwitch";
import { ThemeToggle } from "../ui/ThemeToggle/ThemeToggle";
import { useToast } from "./Toaster";
import { cx } from "./ui";

const BADGE_POLL_MS = 60_000;

interface Item {
  to: string;
  label: string;
  icon: typeof Bell;
  badge?: number;
  end?: boolean;
}

interface Badges {
  citizenUnread: number;
  phcUnread: number;
  citizensFlagged: number;
  pendingApplications: number;
  openConcerns: number;
}

const NONE: Badges = { citizenUnread: 0, phcUnread: 0, citizensFlagged: 0, pendingApplications: 0, openConcerns: 0 };

const ROLE_LABEL: Record<Role, string> = {
  user: "Citizen",
  phc_worker: "PHC worker",
  admin: "Administrator",
  pending_phc: "Awaiting approval",
};

async function loadBadges(role: Role, signal: AbortSignal): Promise<Partial<Badges>> {
  if (role === "user") return { citizenUnread: await getUnreadCount(signal) };
  if (role === "phc_worker") {
    const b = await getPhcBadge(signal);
    return { phcUnread: b.unread, citizensFlagged: b.citizens_flagged };
  }
  if (role === "admin") {
    const o = await getOverview(signal);
    return { pendingApplications: o.pending_applications, openConcerns: o.open_concerns };
  }
  return {};
}

/** What changed since the last check, worded for a toast. Null when nothing grew. */
function newsBetween(before: Badges, after: Badges): { title: string; body: string } | null {
  const grew = (k: keyof Badges) => after[k] - before[k];
  if (grew("citizenUnread") > 0) return { title: "New alert", body: `You have ${after.citizenUnread} unread alert${after.citizenUnread === 1 ? "" : "s"}.` };
  if (grew("citizensFlagged") > 0)
    return { title: "A citizen needs review", body: `${after.citizensFlagged} citizen${after.citizensFlagged === 1 ? " has" : "s have"} open flags.` };
  if (grew("phcUnread") > 0) return { title: "New notification", body: `You have ${after.phcUnread} unread notification${after.phcUnread === 1 ? "" : "s"}.` };
  if (grew("pendingApplications") > 0)
    return { title: "New PHC application", body: `${after.pendingApplications} application${after.pendingApplications === 1 ? " is" : "s are"} waiting.` };
  if (grew("openConcerns") > 0) return { title: "New support concern", body: `${after.openConcerns} concern${after.openConcerns === 1 ? " is" : "s are"} open.` };
  return null;
}

function useBadges(role: Role | undefined) {
  const [badges, setBadges] = useState<Badges>(NONE);
  const last = useRef<Badges | null>(null);
  const { notify } = useToast();
  const location = useLocation();

  useEffect(() => {
    if (!role) return;
    const controller = new AbortController();
    const load = () =>
      loadBadges(role, controller.signal)
        .then((partial) => {
          const next = { ...NONE, ...partial };
          const news = last.current && newsBetween(last.current, next);
          if (news) notify({ tone: "alert", ...news });
          last.current = next;
          setBadges(next);
        })
        .catch(() => undefined);
    void load();
    const timer = window.setInterval(load, BADGE_POLL_MS);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
    // Re-read on navigation: reading the alerts page clears the badge.
  }, [role, location.pathname, notify]);
  return badges;
}

const SIDEBAR_KEY = "hn.sidebar";

function readCollapsed() {
  try {
    return localStorage.getItem(SIDEBAR_KEY) === "collapsed";
  } catch {
    return false;
  }
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

/** The signed-in layout for every role: navigation, badges, sound, theme. */
export function AppShell() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const [sound, setSound] = useState(soundEnabled);
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const hide = collapsed ? "lg:sr-only" : "";

  const toggleCollapsed = () => {
    setCollapsed((c) => {
      try {
        localStorage.setItem(SIDEBAR_KEY, c ? "open" : "collapsed");
      } catch {
        // Storage blocked: the choice lasts until the page reloads.
      }
      return !c;
    });
  };
  const t = useT();
  const location = useLocation();
  const badges = useBadges(user?.role);

  useEffect(() => {
    getPreferences()
      .then((p) => {
        setTheme(p.theme);
        setLanguage(user?.role === "user" ? p.language : "en");
      })
      .catch(() => undefined);
  }, []);
  useEffect(() => setOpen(false), [location.pathname]);

  const toggleSound = () => {
    setSoundEnabled(!sound);
    setSound(!sound);
  };

  const items: Item[] =
    user?.role === "admin"
      ? [
          { to: paths.adminHome, label: "Dashboard", icon: LayoutDashboard, end: true },
          { to: paths.adminApplications, label: "Applications", icon: BadgeCheck, badge: badges.pendingApplications },
          { to: paths.adminAccounts, label: "Accounts", icon: Users },
          { to: paths.adminCentres, label: "Health centres", icon: Building2 },
          { to: paths.adminConcerns, label: "Complaints", icon: LifeBuoy, badge: badges.openConcerns },
          { to: paths.outbreaks, label: "Outbreaks", icon: Activity },
          { to: paths.advisories, label: "Advisories", icon: Megaphone },
          { to: paths.adminAudit, label: "Audit trail", icon: ScrollText },
          { to: paths.assistant, label: "Nira", icon: Sparkles },
        ]
      : user?.role === "phc_worker"
        ? [
            { to: paths.phcHome, label: "Dashboard", icon: LayoutDashboard, end: true },
            { to: paths.phcAlerts, label: "Alerts", icon: Bell, badge: badges.citizensFlagged },
            { to: paths.phcCitizens, label: "Citizens", icon: Users },
            { to: paths.phcSchedule, label: "Schedule", icon: CalendarDays },
            { to: paths.phcReports, label: "Reports", icon: BarChart3 },
            { to: paths.phcMap, label: "Risk map", icon: Map },
            { to: paths.assistant, label: "Nira", icon: Sparkles },
            { to: paths.outbreaks, label: "Outbreaks", icon: Activity },
            { to: paths.advisories, label: "Advisories", icon: Megaphone },
            { to: paths.notifications, label: "Notifications", icon: ClipboardList, badge: badges.phcUnread },
          ]
        : [
            { to: paths.citizenHome, label: t("nav.dashboard"), icon: LayoutDashboard, end: true },
            { to: paths.watch, label: t("nav.watch"), icon: Watch },
            { to: paths.history, label: t("nav.history"), icon: History },
            { to: paths.citizenAlerts, label: t("nav.alerts"), icon: Bell, badge: badges.citizenUnread },
            { to: paths.citizenVisits, label: t("nav.visits"), icon: CalendarDays },
            { to: paths.assistant, label: t("nav.assistant"), icon: Sparkles },
          ];
  // Profile and settings are citizen and worker pages; an admin has neither.
  const account: Item[] =
    user?.role === "admin"
      ? []
      : [
          { to: paths.profile, label: t("nav.profile"), icon: UserRound },
          { to: paths.settings, label: t("nav.settings"), icon: Settings },
        ];

  const iconBtn =
    "grid h-10 w-10 place-items-center rounded-full text-ink-soft transition-colors hover:bg-surface hover:text-ink";
  const toolbar = (
    <div className="flex items-center gap-1">
      {user?.role === "user" && <LanguageSwitch compact className={iconBtn} />}
      <ThemeToggle className={iconBtn} />
      <button type="button" onClick={toggleSound} aria-pressed={sound} title={`${t("shell.sounds")}: ${sound ? t("shell.on") : t("shell.off")}`} className={iconBtn}>
        {sound ? <Volume2 size={18} aria-hidden="true" /> : <VolumeX size={18} aria-hidden="true" />}
        <span className="visually-hidden">{t("shell.sounds")}</span>
      </button>
      {account.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          title={item.label}
          aria-label={item.label}
          className={({ isActive }) => cx(iconBtn, isActive && "bg-lime text-olive")}
        >
          <item.icon size={18} aria-hidden="true" />
        </NavLink>
      ))}
    </div>
  );

  const link = (item: Item) => (
    <NavLink
      key={item.to}
      to={item.to}
      end={item.end}
      title={collapsed ? item.label : undefined}
      className={({ isActive }) =>
        cx(
          "relative flex min-h-11 items-center gap-3 rounded-full px-4 text-sm font-medium transition-colors",
          collapsed && "lg:justify-center lg:px-0",
          isActive ? "bg-paper text-ink shadow-sm" : "text-ink hover:bg-paper/40",
        )
      }
    >
      <item.icon size={18} aria-hidden="true" />
      <span className={cx("flex-1", hide)}>{item.label}</span>
      {!!item.badge && (
        <span
          className={cx(
            "rounded-full bg-ink px-2 py-0.5 text-xs font-semibold text-paper",
            collapsed && "lg:absolute lg:top-0.5 lg:right-1 lg:px-1.5 lg:text-[10px]",
          )}
          aria-label={`${item.badge} new`}
        >
          {item.badge > 99 ? "99+" : item.badge}
        </span>
      )}
    </NavLink>
  );

  return (
    <div className={cx("min-h-dvh bg-paper lg:grid", collapsed ? "lg:grid-cols-[84px_1fr]" : "lg:grid-cols-[264px_1fr]")}>
      <header className="sticky top-0 z-40 flex items-center justify-between border-b border-line bg-paper/90 px-4 py-2 backdrop-blur lg:hidden">
        <Logo />
        <div className="ml-auto mr-1">{toolbar}</div>
        <button
          type="button"
          className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-full text-ink hover:bg-paper-raised"
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
          "relative isolate overflow-clip border-r border-olive/15 bg-matcha p-4 lg:sticky lg:top-0 lg:flex lg:h-dvh lg:flex-col",
          open ? "flex flex-col" : "hidden",
        )}
      >
        <div className={cx("mb-2 hidden items-center gap-2 pt-2 lg:flex", collapsed ? "flex-col" : "justify-between px-2")}>
          {collapsed ? <Logo compact /> : <Logo />}
          <button
            type="button"
            onClick={toggleCollapsed}
            aria-expanded={!collapsed}
            aria-controls="app-nav"
            title={collapsed ? "Show the sidebar" : "Hide the sidebar"}
            className="grid h-10 w-10 shrink-0 place-items-center rounded-full text-ink hover:bg-paper/40"
          >
            {collapsed ? <PanelLeftOpen size={18} aria-hidden="true" /> : <PanelLeftClose size={18} aria-hidden="true" />}
            <span className="visually-hidden">{collapsed ? "Show the sidebar" : "Hide the sidebar"}</span>
          </button>
        </div>
        {user && (
          <p className={cx("mb-5 hidden px-2", !collapsed && "lg:block")}>
            <span className="inline-flex items-center rounded-full border border-olive/20 bg-paper/60 px-3 py-1 text-xs font-semibold text-ink">
              {ROLE_LABEL[user.role]}
            </span>
          </p>
        )}
        <nav aria-label="Main" className="flex flex-col gap-1">
          {items.map(link)}
        </nav>
        <div className="mt-6 lg:mt-auto">
          {!collapsed && <Doodle piece="beads" className="static! -mb-2! ml-auto w-20 lg:block!" />}
          <nav aria-label="Account" className="flex flex-col gap-1 border-t border-olive/20 pt-3">
            <button
              type="button"
              onClick={() => void logout()}
              title={collapsed ? "Sign out" : undefined}
              className={cx(
                "flex min-h-11 items-center gap-3 rounded-full px-4 text-sm font-medium text-ink transition-colors hover:bg-paper/40",
                collapsed && "lg:justify-center lg:px-0",
              )}
            >
              <LogOut size={18} aria-hidden="true" />
              <span className={hide}>{t("shell.signOut")}</span>
            </button>
          </nav>
          {user && (
            <div
              className={cx("mt-3 flex items-center gap-3 rounded-3xl border border-olive/15 bg-paper/70 p-3", collapsed && "lg:justify-center lg:border-0 lg:bg-transparent lg:p-0")}
              title={collapsed ? `${user.name} · ${user.email}` : undefined}
            >
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-olive font-display text-base text-paper" aria-hidden="true">
                {initials(user.name)}
              </span>
              <span className={cx("min-w-0", hide)}>
                <span className="block truncate text-sm font-semibold text-ink">{user.name}</span>
                <span className="block truncate text-xs text-ink-muted">{user.email}</span>
              </span>
            </div>
          )}
        </div>
      </aside>
      <div className="min-w-0">
        <div className="sticky top-0 z-30 hidden h-14 items-center justify-end border-b border-line bg-paper/90 px-6 backdrop-blur lg:flex">
          {toolbar}
        </div>
        <main className={location.pathname === paths.assistant ? "min-w-0" : "mx-auto w-full max-w-6xl px-4 py-6 md:px-8 md:py-10"}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
