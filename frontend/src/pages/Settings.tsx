import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { Building2, Download, ShieldAlert } from "lucide-react";
import { Btn, Card, Empty, ErrorNote, Labelled, Loading, PageHeader, Tabs, cx, inputCls } from "../components/app/ui";
import { useAuth } from "../context/AuthContext";
import { fmtDate, fmtDateTime } from "../lib/format";
import { oneOf, useQueryState } from "../lib/params";
import { paths } from "../lib/routes";
import { setTheme } from "../lib/theme";
import { useResource } from "../lib/useResource";
import { errorMessage } from "../services/api";
import * as account from "../services/account";
import type { ConsentType, Preferences } from "../services/account";

const TABS = ["account", "preferences", "privacy", "support", "centre", "work"] as const;
type Tab = (typeof TABS)[number];

function Saved({ message }: { message: string | null }) {
  return message ? <p role="status" className="text-sm text-success">{message}</p> : null;
}

function Toggle({ checked, onChange, label, hint, disabled }: { checked: boolean; onChange: (v: boolean) => void; label: ReactNode; hint?: ReactNode; disabled?: boolean }) {
  return (
    <label className="flex items-start gap-3 py-2">
      <input type="checkbox" className="mt-1" checked={checked} disabled={disabled} onChange={(e) => onChange(e.target.checked)} />
      <span className="text-sm">
        <span className="font-medium text-ink">{label}</span>
        {hint && <span className="block text-ink-soft">{hint}</span>}
      </span>
    </label>
  );
}

// --- Account & security -----------------------------------------------------

function AccountTab() {
  const { logout } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [deactPassword, setDeactPassword] = useState("");
  const [deactConfirm, setDeactConfirm] = useState("");
  const [deactErr, setDeactErr] = useState<string | null>(null);

  const change = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    setMsg(null);
    try {
      setMsg((await account.changePassword(current, next)).detail);
      setCurrent("");
      setNext("");
    } catch (e2) {
      setErr(errorMessage(e2));
    } finally {
      setBusy(false);
    }
  };

  const deactivate = async (e: FormEvent) => {
    e.preventDefault();
    setDeactErr(null);
    try {
      await account.deactivate(deactPassword);
      await logout();
    } catch (e2) {
      setDeactErr(errorMessage(e2));
    }
  };

  return (
    <div className="flex max-w-xl flex-col gap-6">
      <Card title="Change password">
        <form onSubmit={change} className="flex flex-col gap-3">
          <Labelled label="Current password"><input type="password" autoComplete="current-password" required value={current} onChange={(e) => setCurrent(e.target.value)} className={inputCls} /></Labelled>
          <Labelled label="New password" hint="At least 8 characters. Your other devices will be signed out.">
            <input type="password" autoComplete="new-password" required minLength={8} value={next} onChange={(e) => setNext(e.target.value)} className={inputCls} />
          </Labelled>
          {err && <p className="text-sm text-danger">{err}</p>}
          <Saved message={msg} />
          <div><Btn tone="primary" type="submit" busy={busy}>Change password</Btn></div>
        </form>
      </Card>
      <Card title="Signed-in devices">
        <Link to={paths.sessions} className="text-sm font-semibold text-brand underline">See and sign out other sessions</Link>
      </Card>
      <Card title="Deactivate account">
        <form onSubmit={deactivate} className="flex flex-col gap-3">
          <p className="text-sm text-ink-soft">You will be signed out everywhere and any booked visits will be cancelled. An administrator can reactivate the account.</p>
          <Labelled label="Password"><input type="password" required value={deactPassword} onChange={(e) => setDeactPassword(e.target.value)} className={inputCls} /></Labelled>
          <Labelled label='Type DEACTIVATE to confirm'><input value={deactConfirm} onChange={(e) => setDeactConfirm(e.target.value)} className={inputCls} /></Labelled>
          {deactErr && <p className="text-sm text-danger">{deactErr}</p>}
          <div><Btn tone="danger" type="submit" disabled={deactConfirm !== "DEACTIVATE" || !deactPassword}>Deactivate my account</Btn></div>
        </form>
      </Card>
    </div>
  );
}

// --- Preferences ------------------------------------------------------------

function PreferencesTab() {
  const prefs = useResource(() => account.getPreferences(), "prefs");
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [local, setLocal] = useState<Preferences | null>(null);
  useEffect(() => setLocal(prefs.data), [prefs.data]);

  const save = async (patch: Parameters<typeof account.updatePreferences>[0]) => {
    setErr(null);
    try {
      const saved = await account.updatePreferences(patch);
      setLocal(saved);
      setTheme(saved.theme);
      setMsg("Saved.");
    } catch (e) {
      setErr(errorMessage(e));
    }
  };

  if (prefs.error) return <ErrorNote message={prefs.error} onRetry={prefs.reload} />;
  if (!local) return <Loading />;
  const channels = [
    { key: "alerts", label: "Health alerts" },
    { key: "surveillance", label: "Community health notices" },
    { key: "announcements", label: "Announcements" },
  ] as const;

  return (
    <div className="flex max-w-xl flex-col gap-6">
      <Card title="Appearance">
        <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Theme">
          {(["system", "light", "dark"] as const).map((t) => (
            <button key={t} type="button" role="radio" aria-checked={local.theme === t} onClick={() => void save({ theme: t })}
              className={cx("min-h-10 rounded-xl border px-4 text-sm capitalize", local.theme === t ? "border-brand bg-brand-soft text-brand" : "border-line text-ink")}>
              {t === "system" ? "Match device" : t}
            </button>
          ))}
        </div>
      </Card>
      <Card title="Notifications">
        <table className="w-full text-sm">
          <thead className="text-xs text-ink-soft"><tr><th className="py-1 text-left font-medium">About</th><th className="font-medium">In app</th><th className="font-medium">Email</th><th className="font-medium">SMS</th></tr></thead>
          <tbody>
            {channels.map((c) => (
              <tr key={c.key}>
                <td className="py-2 text-ink">{c.label}</td>
                {(["in_app", "email", "sms"] as const).map((ch) => (
                  <td key={ch} className="text-center">
                    <input type="checkbox" aria-label={`${c.label} by ${ch.replace("_", " ")}`} checked={local.notifications[c.key][ch]}
                      onChange={(e) => void save({ notifications: { [c.key]: { [ch]: e.target.checked } } })} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      {err && <p className="text-sm text-danger">{err}</p>}
      <Saved message={msg} />
    </div>
  );
}

// --- Privacy ----------------------------------------------------------------

const CONSENT_TEXT: Record<ConsentType, { label: string; hint: string }> = {
  health_tracking: { label: "Health tracking", hint: "Store and score the readings you log. Turning this off stops new readings being saved." },
  phc_worker_access: { label: "Health worker access", hint: "Health workers at your centre can see your readings to follow up." },
  community_surveillance: { label: "Community health monitoring", hint: "Your readings count, without your name, towards area-level outbreak signals." },
  research_analytics: { label: "Research", hint: "Anonymised data may be used for public-health research." },
  marketing_updates: { label: "Product updates", hint: "Occasional news about HealthNexus." },
};

function PrivacyTab() {
  const { user, refreshUser } = useAuth();
  const consents = useResource(() => Promise.all([account.getConsents(), account.getConsentHistory(), account.getAbout()]), "consents");
  const [err, setErr] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  if (consents.error) return <ErrorNote message={consents.error} onRetry={consents.reload} />;
  if (!consents.data) return <Loading />;
  const [current, history, about] = consents.data;
  const types = (Object.keys(CONSENT_TEXT) as ConsentType[]).filter((t) => user?.role === "user" || !["health_tracking", "phc_worker_access", "community_surveillance"].includes(t));

  const change = async (type: ConsentType, granted: boolean) => {
    setErr(null);
    try {
      await account.updateConsent(type, granted);
      if (type === "health_tracking") await refreshUser();
      consents.reload();
    } catch (e) {
      setErr(errorMessage(e));
    }
  };

  return (
    <div className="flex max-w-2xl flex-col gap-6">
      <Card title="Who can see your data">
        <p className="text-sm text-ink">{about.who_can_see}</p>
        <p className="mt-2 text-sm text-ink-soft">{about.scoring_note}</p>
      </Card>
      <Card title="Consent">
        {types.map((t) => (
          <Toggle key={t} checked={current.consents[t] === true} onChange={(v) => void change(t, v)} label={CONSENT_TEXT[t].label}
            hint={<>{CONSENT_TEXT[t].hint}{current.consents[t] === null && " (Not answered yet.)"}</>} />
        ))}
        {err && <p className="text-sm text-danger">{err}</p>}
      </Card>
      <Card title="Your data" aside={<Btn busy={downloading} onClick={async () => { setDownloading(true); try { await account.downloadExport(); } catch (e) { setErr(errorMessage(e)); } finally { setDownloading(false); } }}><Download size={16} aria-hidden="true" /> Download a copy</Btn>}>
        <p className="text-sm text-ink-soft">
          We hold {about.data_held.readings} readings, {about.data_held.alerts} alerts, {about.data_held.visits} visits and {about.data_held.concerns} support requests for you.
        </p>
      </Card>
      <Card title="Consent history">
        {history.length === 0 ? <p className="text-sm text-ink-soft">No changes recorded.</p> : (
          <ul className="flex flex-col gap-1 text-sm">
            {history.map((h) => (
              <li key={h.id} className="flex flex-wrap justify-between gap-2">
                <span className="text-ink">{CONSENT_TEXT[h.consent_type].label}: {h.granted ? "allowed" : "not allowed"}</span>
                <span className="text-ink-soft">{fmtDateTime(h.created_at)} · {h.source}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
      <p className="text-xs text-ink-soft">{about.app} {about.version}</p>
    </div>
  );
}

// --- Support ----------------------------------------------------------------

const CATEGORIES: { value: account.Concern["category"]; label: string }[] = [
  { value: "incorrect_diagnosis_flag", label: "A flag on my reading looks wrong" },
  { value: "data_misuse", label: "Misuse of my data" },
  { value: "access_request", label: "Request access to my data" },
  { value: "harassment", label: "Harassment" },
  { value: "other", label: "Something else" },
];

function SupportTab() {
  const list = useResource(() => account.listConcerns(), "concerns");
  const [category, setCategory] = useState<account.Concern["category"]>("other");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const c = await account.raiseConcern(category, description);
      setMsg(`Thanks. Your reference is ${c.ticket_ref}.`);
      setDescription("");
      list.reload();
    } catch (e2) {
      setErr(errorMessage(e2));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex max-w-2xl flex-col gap-6">
      <Card title="Raise a concern">
        <form onSubmit={submit} className="flex flex-col gap-3">
          <Labelled label="About">
            <select value={category} onChange={(e) => setCategory(e.target.value as account.Concern["category"])} className={inputCls}>
              {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
          </Labelled>
          <Labelled label="What happened" hint={`${description.trim().length}/2000, at least 10 characters`}>
            <textarea value={description} maxLength={2000} rows={4} onChange={(e) => setDescription(e.target.value)} className={cx(inputCls, "py-2")} />
          </Labelled>
          {err && <p className="text-sm text-danger">{err}</p>}
          <Saved message={msg} />
          <div><Btn tone="primary" type="submit" busy={busy} disabled={description.trim().length < 10}>Send</Btn></div>
        </form>
      </Card>
      <Card title="Your requests">
        {!list.data ? <Loading /> : list.data.length === 0 ? <p className="text-sm text-ink-soft">None yet.</p> : (
          <ul className="divide-y divide-line">
            {list.data.map((c) => (
              <li key={c.id} className="py-3 text-sm">
                <div className="flex flex-wrap justify-between gap-2">
                  <span className="font-mono text-ink">{c.ticket_ref}</span>
                  <span className="capitalize text-ink-soft">{c.status.replace("_", " ")} · {fmtDate(c.created_at)}</span>
                </div>
                <p className="text-ink">{c.description}</p>
                {c.admin_note && <p className="mt-1 rounded-lg bg-paper-raised p-2 text-ink">Reply: {c.admin_note}</p>}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

// --- Role tabs --------------------------------------------------------------

function CentreTab() {
  const { refreshUser } = useAuth();
  const centre = useResource(() => account.getHealthCentre(), "centre");
  const [confirm, setConfirm] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  if (centre.error) return <ErrorNote message={centre.error} onRetry={centre.reload} />;
  if (!centre.data) return <Loading />;
  const c = centre.data;

  const change = async (id: string) => {
    setBusy(true);
    setErr(null);
    try {
      await account.changeHealthCentre(id);
      await refreshUser();
      setConfirm(null);
      centre.reload();
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex max-w-2xl flex-col gap-6">
      <Card title="Your health centre">
        {c.current ? (
          <div className="flex gap-3">
            <Building2 size={22} className="shrink-0 text-brand" aria-hidden="true" />
            <div className="text-sm">
              <p className="font-semibold text-ink">{c.current.name}</p>
              <p className="text-ink-soft">{[c.current.block, c.district].filter(Boolean).join(", ")}</p>
              {c.current.workers_assigned > 0 ? (
                <p className="mt-1 text-success">{c.current.workers_assigned === 1 ? "1 health worker reviews" : `${c.current.workers_assigned} health workers review`} your readings.</p>
              ) : null}
            </div>
          </div>
        ) : (
          <p className="text-sm text-ink-soft">Not linked to a health centre.</p>
        )}
        {(!c.current || c.current.workers_assigned === 0) && (
          <p role="alert" className="mt-3 flex gap-2 rounded-xl bg-danger-soft p-3 text-sm text-danger">
            <ShieldAlert size={18} className="shrink-0" aria-hidden="true" />
            <span><strong>Nobody is reviewing your readings.</strong> No health worker is assigned to {c.current ? "this centre" : "you"}. Choose a staffed centre below, and see a doctor if you feel unwell.</span>
          </p>
        )}
      </Card>
      <Card title={`Centres in ${c.district ?? "your district"}`}>
        {c.options.length === 0 ? <Empty title="No centres found for your district" /> : (
          <ul className="divide-y divide-line">
            {c.options.map((o) => (
              <li key={o.id} className="flex flex-wrap items-center gap-3 py-3 text-sm">
                <div className="flex-1">
                  <p className="font-medium text-ink">{o.name}{o.is_current && <span className="ml-2 text-xs text-brand">current</span>}</p>
                  <p className={o.workers_assigned ? "text-ink-soft" : "text-danger"}>
                    {o.block ? `${o.block} · ` : ""}{o.workers_assigned ? `${o.workers_assigned} health worker${o.workers_assigned > 1 ? "s" : ""}` : "No health worker assigned"}
                  </p>
                </div>
                {!o.is_current && (confirm === o.id ? (
                  <span className="flex items-center gap-2">
                    <Btn tone="primary" busy={busy} onClick={() => void change(o.id)}>Switch</Btn>
                    <Btn tone="ghost" onClick={() => setConfirm(null)}>Keep current</Btn>
                  </span>
                ) : (
                  <Btn onClick={() => setConfirm(o.id)}>Switch here</Btn>
                ))}
              </li>
            ))}
          </ul>
        )}
        {confirm && <p className="mt-2 text-xs text-ink-soft">Switching moves your readings to the new centre's workers. Visits booked by your current centre will be cancelled.</p>}
        {err && <p className="mt-2 text-sm text-danger">{err}</p>}
      </Card>
    </div>
  );
}

function WorkTab() {
  const prefs = useResource(() => Promise.all([account.getPreferences(), account.getProfile()]), "work");
  const [start, setStart] = useState("09:00");
  const [end, setEnd] = useState("17:00");
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    if (prefs.data) {
      setStart(prefs.data[0].working_hours.start);
      setEnd(prefs.data[0].working_hours.end);
    }
  }, [prefs.data]);
  if (prefs.error) return <ErrorNote message={prefs.error} onRetry={prefs.reload} />;
  if (!prefs.data) return <Loading />;
  const profile = prefs.data[1];

  const save = async (e: FormEvent) => {
    e.preventDefault();
    setErr(null);
    try {
      await account.updatePreferences({ working_hours: { start, end } });
      setMsg("Saved.");
    } catch (e2) {
      setErr(errorMessage(e2));
    }
  };

  return (
    <div className="flex max-w-xl flex-col gap-6">
      <Card title="Your facility">
        <p className="text-sm text-ink">{profile.facility ?? "Not linked to a facility. Contact support: without one, no readings reach you."}</p>
        {profile.designation && <p className="text-sm capitalize text-ink-soft">{profile.designation.replace(/_/g, " ")}</p>}
      </Card>
      <Card title="Working hours">
        <form onSubmit={save} className="flex flex-wrap items-end gap-3">
          <Labelled label="Start"><input type="time" value={start} onChange={(e) => setStart(e.target.value)} className={inputCls} /></Labelled>
          <Labelled label="End"><input type="time" value={end} onChange={(e) => setEnd(e.target.value)} className={inputCls} /></Labelled>
          <Btn tone="primary" type="submit">Save</Btn>
        </form>
        <p className="mt-2 text-xs text-ink-soft">New visits are suggested at the start of your working day.</p>
        {err && <p className="mt-2 text-sm text-danger">{err}</p>}
        <Saved message={msg} />
      </Card>
    </div>
  );
}

export function Settings() {
  const { user } = useAuth();
  const { params, set } = useQueryState();
  const roleTab: Tab = user?.role === "phc_worker" ? "work" : "centre";
  const tab = oneOf(params.get("tab"), TABS, "account");
  const active = tab === "centre" || tab === "work" ? roleTab : tab;

  return (
    <>
      <PageHeader title="Settings" />
      <Tabs
        label="Settings sections"
        value={active}
        onChange={(t) => set({ tab: t === "account" ? null : t })}
        tabs={[
          { id: "account", label: "Account & security" },
          { id: "preferences", label: "Preferences" },
          { id: "privacy", label: "Privacy" },
          { id: "support", label: "Support" },
          { id: roleTab, label: roleTab === "work" ? "Your work" : "Your health centre" },
        ]}
      />
      {active === "account" && <AccountTab />}
      {active === "preferences" && <PreferencesTab />}
      {active === "privacy" && <PrivacyTab />}
      {active === "support" && <SupportTab />}
      {active === "centre" && <CentreTab />}
      {active === "work" && <WorkTab />}
    </>
  );
}
