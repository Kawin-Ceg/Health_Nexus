import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import { Building2, CheckCircle2, CircleStop, Eye, Lock, MapPin, Megaphone, Radio, ThumbsDown, ThumbsUp, Trash2, Undo2, Users, X, XCircle } from "lucide-react";
import { Btn, Card, Empty, ErrorNote, Labelled, Loading, PageHeader, SearchInput, cx, inputCls, Status, type StatusTone } from "../components/app/ui";
import { useToast } from "../components/app/Toaster";
import { useAuth } from "../context/AuthContext";
import { fmtDate, fmtDateTime } from "../lib/format";
import { useResource } from "../lib/useResource";
import {
  checkRed,
  getTargets,
  listAdvisories,
  previewReach,
  publishAdvisory,
  reviewAdvisory,
  withdrawAdvisory,
  type Advisory,
  type AdvisoryInput,
  type RedCheck,
  type Target,
} from "../services/advisories";
import { errorMessage } from "../services/api";

type Level = Advisory["severity"];

const LEVELS: Record<Level, { name: string; meaning: string; dot: string; tone: StatusTone; ring: string; bar: string }> = {
  low: {
    name: "Green",
    meaning: "For information",
    dot: "bg-green-600",
    tone: "success",
    ring: "border-green-600 bg-green-50",
    bar: "border-l-green-600",
  },
  medium: {
    name: "Yellow",
    meaning: "Take precautions",
    dot: "bg-yellow-400",
    tone: "warn",
    ring: "border-yellow-400 bg-yellow-50",
    bar: "border-l-yellow-400",
  },
  high: {
    name: "Red",
    meaning: "Emergency, act now",
    dot: "bg-red-600",
    tone: "danger",
    ring: "border-red-600 bg-red-50",
    bar: "border-l-red-600",
  },
};

const PERIODS = [
  { id: "all", label: "Any time", days: 0 },
  { id: "7", label: "Last 7 days", days: 7 },
  { id: "30", label: "Last 30 days", days: 30 },
  { id: "90", label: "Last 3 months", days: 90 },
  { id: "365", label: "Last year", days: 365 },
    ] as const;

function LevelPill({ level }: { level: Level }) {
  const l = LEVELS[level];
  return (
    <Status tone={l.tone}>{l.name}</Status>
  );
}

function StatePill({ a }: { a: Advisory }) {
  if (a.withdrawn_at) return <Status tone="neutral" icon={Undo2}>Withdrawn</Status>;
  return a.active ? <Status tone="progress" icon={Radio}>Running</Status> : <Status tone="neutral" icon={CircleStop}>Ended</Status>;
}

export function Advisories() {
  const { user } = useAuth();
  const admin = user?.role === "admin";
  const list = useResource((s) => listAdvisories(true, s), "advisories-all");
  const [openId, setOpenId] = useState<string | null>(null);
  const open = list.data?.find((a) => a.id === openId) ?? null;

  const audience = admin ? (user?.district ? `people in ${user.district} district` : "people across the state") : "the people your health centre serves";

  return (
    <>
      <PageHeader
        title="Community advisories"
        lead={`Notices for ${audience}. They appear on citizens' Alerts page until they expire or you withdraw them.`}
      />
      <Compose admin={admin} area={user?.district ?? null} onPublished={list.reload} />
      <History list={list.data} error={list.error} reload={list.reload} onOpen={setOpenId} />
      {open && <Details advisory={open} onClose={() => setOpenId(null)} onChanged={list.reload} />}
    </>
  );
}

function Compose({ admin, area, onPublished }: { admin: boolean; area: string | null; onPublished: () => void }) {
  const [params, setParams] = useSearchParams();
  const clusterId = params.get("cluster");
  const [title, setTitle] = useState(params.get("title") ?? "");
  const [body, setBody] = useState(params.get("body") ?? "");
  const [level, setLevel] = useState<Level>("medium");
  const [reason, setReason] = useState("");
  const [days, setDays] = useState(14);
  const [target, setTarget] = useState<Target>(admin ? (area ? { scope: "district", district: area } : { scope: "state" }) : { scope: "centre" });
  const [check, setCheck] = useState<RedCheck | null>(null);
  const [checking, setChecking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { notify } = useToast();

  const pick = async (next: Level) => {
    if (next !== "high") {
      setLevel(next);
      return;
    }
    setChecking(true);
    try {
      const result = await checkRed(clusterId);
      setCheck(result);
      setLevel(result.allowed ? "high" : "medium");
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setChecking(false);
    }
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const input: AdvisoryInput = {
        ...target,
        title,
        body,
        severity: level,
        days,
        ...(level === "high" ? { red_reason: reason } : {}),
        ...(clusterId ? { cluster_id: clusterId } : {}),
      };
      const made = await publishAdvisory(input);
      notify({ tone: "success", title: "Advisory published", body: `${made.audience}: ${made.reach ?? 0} citizens` });
      setTitle("");
      setBody("");
      setReason("");
      setLevel("medium");
      setCheck(null);
      if (clusterId) setParams({}, { replace: true });
      onPublished();
    } catch (e2) {
      setError(errorMessage(e2));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title={<span className="flex items-center gap-2"><Megaphone size={20} aria-hidden="true" /> New advisory</span>} className="mb-8">
      <form onSubmit={submit} className="grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <div className="flex flex-col gap-4">
          {clusterId && <p className="rounded-2xl bg-paper p-3 text-sm text-ink-soft">Drafted from an outbreak signal. Edit it before publishing.</p>}
          <Labelled label="Title">
            <input required minLength={4} maxLength={120} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Dengue precautions" className={inputCls} />
          </Labelled>
          <Labelled label="Message" hint={`${body.length}/2000. Plain words: what is happening and what people should do.`}>
            <textarea required minLength={10} maxLength={2000} rows={6} value={body} onChange={(e) => setBody(e.target.value)} className={cx(inputCls, "py-3")} />
          </Labelled>
          <Audience admin={admin} area={area} value={target} onChange={setTarget} />
        </div>

        <div className="flex flex-col gap-4">
          <fieldset>
            <legend className="mb-2 text-sm font-medium text-ink">How important</legend>
            <div className="grid grid-cols-3 gap-2">
              {(["low", "medium", "high"] as Level[]).map((l) => (
                <button
                  key={l}
                  type="button"
                  aria-pressed={level === l}
                  disabled={checking}
                  onClick={() => void pick(l)}
                  className={cx(
                    "flex flex-col items-start gap-1 rounded-xl border-2 p-3 text-left transition-colors",
                    level === l ? LEVELS[l].ring : "border-line bg-surface hover:border-ink/25",
                  )}
                >
                  <span className="flex items-center gap-1.5 text-sm font-semibold text-ink">
                    <span className={cx("h-2.5 w-2.5 rounded-full", LEVELS[l].dot)} aria-hidden="true" />
                    {LEVELS[l].name}
                    {l === "high" && level !== "high" && <Lock size={12} className="text-ink-muted" aria-label="needs a check" />}
                  </span>
                  <span className="text-xs text-ink-soft">{checking && l === "high" ? "Checking…" : LEVELS[l].meaning}</span>
                </button>
              ))}
            </div>
            <p className="mt-2 text-xs text-ink-muted">Use green or yellow for most notices. Red is only allowed when the data shows a real emergency.</p>
          </fieldset>

          {check && (
            <div className={cx("rounded-xl border p-3 text-sm", check.allowed ? "border-red-200 bg-red-50/60" : "border-amber-200 bg-amber-50/70")}>
              <p className="mb-2 font-semibold text-ink">{check.message}</p>
              <ul className="flex flex-col gap-1.5">
                {check.checks.map((c) => (
                  <li key={c.label} className="flex gap-2">
                    {c.met ? <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-green-700" aria-label="met" /> : <XCircle size={16} className="mt-0.5 shrink-0 text-ink-muted" aria-label="not met" />}
                    <span>
                      <span className="text-ink">{c.label}</span>
                      <span className="block text-xs text-ink-soft">{c.value}</span>
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {level === "high" && (
            <Labelled label="Why does this need red?" hint={`${reason.length}/1000. At least 30 characters. Kept in the audit trail.`}>
              <textarea required minLength={30} maxLength={1000} rows={3} value={reason} onChange={(e) => setReason(e.target.value)} className={cx(inputCls, "py-3")} />
            </Labelled>
          )}

          <Labelled label="Show for">
            <select value={days} onChange={(e) => setDays(Number(e.target.value))} className={inputCls}>
              {[3, 7, 14, 30, 60, 90].map((d) => (
                <option key={d} value={d}>{d} days</option>
              ))}
            </select>
          </Labelled>
          {error && <p className="text-sm text-danger">{error}</p>}
          <div className="mt-auto">
            <Btn tone="primary" type="submit" busy={busy}>Publish</Btn>
          </div>
        </div>
      </form>
    </Card>
  );
}

function Audience({ admin, area, value, onChange }: { admin: boolean; area: string | null; value: Target; onChange: (t: Target) => void }) {
  const options = useResource((s) => getTargets(s), "advisory-targets");
  const ready = (value.scope !== "centre" || !admin || !!value.phc_id) && (value.scope !== "area" || !!value.area);
  const reach = useResource((s) => (ready ? previewReach(value, s) : Promise.resolve(null)), `reach-${JSON.stringify(value)}`);
  const o = options.data;
  const centre = o?.centres.find((c) => c.id === value.phc_id) ?? (admin ? null : o?.centres[0]);
  const nearby = value.radius_km != null;

  const modes = [
    ...(admin ? [{ id: "district" as const, icon: Users, label: area ? `All of ${area}` : "Whole state", hint: "Every citizen in the district" }] : []),
    { id: "centre" as const, icon: Building2, label: admin ? "A health centre" : "My centre", hint: "Its citizens, and people living near it" },
    ...(admin ? [{ id: "area" as const, icon: MapPin, label: "A locality", hint: "Everyone living there, registered or not" }] : []),
  ];
  const setMode = (id: (typeof modes)[number]["id"]) =>
    onChange(id === "district" ? (area ? { scope: "district", district: area } : { scope: "state" }) : { scope: id, district: area ?? undefined });

  return (
    <fieldset className="flex flex-col gap-3">
      <legend className="mb-2 text-sm font-medium text-ink">Who gets it</legend>
      <div className={cx("grid gap-2", modes.length === 3 ? "sm:grid-cols-3" : "sm:grid-cols-2")}>
        {modes.map((m) => {
          const on = m.id === "district" ? value.scope === "district" || value.scope === "state" : value.scope === m.id;
          return (
            <button
              key={m.id}
              type="button"
              aria-pressed={on}
              onClick={() => setMode(m.id)}
              className={cx("flex items-start gap-2 rounded-xl border-2 p-3 text-left transition-colors", on ? "border-matcha bg-matcha/15" : "border-line bg-surface hover:border-ink/25")}
            >
              <m.icon size={18} className="mt-0.5 shrink-0 text-ink-soft" aria-hidden="true" />
              <span>
                <span className="block text-sm font-semibold text-ink">{m.label}</span>
                <span className="block text-xs text-ink-soft">{m.hint}</span>
              </span>
            </button>
          );
        })}
      </div>

      {value.scope === "centre" && (
        <div className="flex flex-col gap-3">
          {admin ? (
            <Labelled label="Health centre">
              <select required value={value.phc_id ?? ""} onChange={(e) => onChange({ ...value, phc_id: e.target.value || undefined })} className={inputCls}>
                <option value="">Choose…</option>
                {o?.centres.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                    {c.block ? ` · ${c.block}` : ""} ({c.citizens} registered)
                  </option>
                ))}
              </select>
            </Labelled>
          ) : (
            <p className="text-sm font-semibold text-ink">{centre?.name ?? "Your centre"}</p>
          )}
          <div className="flex flex-wrap items-center gap-3">
            <label className={cx("flex min-h-11 items-center gap-2 text-sm", centre && !centre.located ? "text-ink-muted" : "text-ink")}>
              <input
                type="checkbox"
                checked={nearby}
                disabled={!!centre && !centre.located}
                onChange={(e) => onChange({ ...value, radius_km: e.target.checked ? 3 : undefined })}
              />
              Also people living nearby who are not registered here
            </label>
            {nearby && (
              <select aria-label="Distance" value={value.radius_km} onChange={(e) => onChange({ ...value, radius_km: Number(e.target.value) })} className={cx(inputCls, "w-auto px-3")}>
                {[1, 2, 3, 5, 10].map((k) => (
                  <option key={k} value={k}>within {k} km</option>
                ))}
              </select>
            )}
          </div>
          {centre && !centre.located && <p className="text-xs text-warn">This centre has no map location yet, so nearby residents cannot be found.</p>}
        </div>
      )}

      {value.scope === "area" && (
        <Labelled label="Locality or pincode">
          <select required value={value.area ?? ""} onChange={(e) => onChange({ ...value, area: e.target.value || undefined })} className={inputCls}>
            <option value="">Choose…</option>
            <optgroup label="Localities">
              {o?.localities.map((l) => (
                <option key={l.name} value={l.name}>{l.name} ({l.citizens})</option>
              ))}
            </optgroup>
            <optgroup label="Pincodes">
              {o?.pincodes.map((l) => (
                <option key={l.name} value={l.name}>{l.name} ({l.citizens})</option>
              ))}
            </optgroup>
          </select>
        </Labelled>
      )}

      <p className="flex items-center gap-2 rounded-xl bg-paper px-3 py-2 text-sm text-ink-soft">
        <Users size={16} className="shrink-0" aria-hidden="true" />
        {!ready ? (
          "Choose who gets it to see how many people it reaches."
        ) : reach.error ? (
          <span className="text-danger">{reach.error}</span>
        ) : !reach.data ? (
          "Counting…"
        ) : (
          <span>
            Reaches <strong className="text-ink">{reach.data.citizens}</strong> citizen{reach.data.citizens === 1 ? "" : "s"}
            {value.scope === "centre"
              ? nearby
                ? ` · ${reach.data.registered} registered here, ${reach.data.citizens - reach.data.registered} living nearby`
                : ""
              : ` · ${reach.data.citizens - reach.data.registered} not linked to any centre`}
          </span>
        )}
      </p>
    </fieldset>
  );
}

function History({ list, error, reload, onOpen }: { list: Advisory[] | null | undefined; error?: string | null; reload: () => void; onOpen: (id: string) => void }) {
  const [search, setSearch] = useState("");
  const [period, setPeriod] = useState<(typeof PERIODS)[number]["id"]>("all");
  const [level, setLevel] = useState<Level | "all">("all");
  const [withdrawing, setWithdrawing] = useState<string | null>(null);
  const { notify } = useToast();

  const withdraw = async (a: Advisory) => {
    if (!window.confirm(`Withdraw "${a.title}"? Citizens stop seeing it straight away.`)) return;
    setWithdrawing(a.id);
    try {
      await withdrawAdvisory(a.id);
      notify({ tone: "success", title: "Advisory withdrawn", body: a.title });
      reload();
    } catch (e) {
      notify({ tone: "alert", title: "Could not withdraw", body: errorMessage(e) });
    } finally {
      setWithdrawing(null);
    }
  };

  const rows = useMemo(() => {
    const days = PERIODS.find((p) => p.id === period)?.days ?? 0;
    const since = days ? Date.now() - days * 86_400_000 : 0;
    const q = search.trim().toLowerCase();
    return (list ?? []).filter(
      (a) =>
        (level === "all" || a.severity === level) &&
        new Date(a.created_at).getTime() >= since &&
        (!q || `${a.title} ${a.body} ${a.author ?? ""}`.toLowerCase().includes(q)),
    );
  }, [list, search, period, level]);

  return (
    <section aria-labelledby="advisory-history">
      <h2 id="advisory-history" className="mb-3 text-xl text-ink">Advisory history</h2>
      <div className="mb-4 grid gap-3 md:grid-cols-[3fr_2fr]">
        <SearchInput value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search title, message or author" aria-label="Search advisories" />
        <div className="grid grid-cols-2 gap-3">
          <select aria-label="When given" value={period} onChange={(e) => setPeriod(e.target.value as typeof period)} className={cx(inputCls, "px-3")}>
            {PERIODS.map((p) => (
              <option key={p.id} value={p.id}>{p.label}</option>
            ))}
          </select>
          <select aria-label="Importance" value={level} onChange={(e) => setLevel(e.target.value as typeof level)} className={cx(inputCls, "px-3")}>
            <option value="all">All levels</option>
            <option value="low">Green</option>
            <option value="medium">Yellow</option>
            <option value="high">Red</option>
          </select>
        </div>
      </div>
      {error && <ErrorNote message={error} onRetry={reload} />}
      {!list ? (
        !error && <Loading />
      ) : rows.length === 0 ? (
        <Empty title={list.length ? "Nothing matches these filters" : "No advisories yet"} />
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
                <th className="w-36 px-4 py-3"><span className="visually-hidden">Withdraw</span></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((a, i) => (
                <tr key={a.id} onClick={() => onOpen(a.id)} className="cursor-pointer align-top hover:bg-paper">
                  <td className="px-4 py-3 tabular-nums text-ink-muted">{i + 1}</td>
                  <td className="px-4 py-3">
                    <span className="block font-semibold text-ink">{a.title}</span>
                    <span className="block text-xs text-ink-soft">
                      {a.audience} · {fmtDateTime(a.created_at)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="flex flex-col items-start gap-2">
                      <StatePill a={a} />
                      {a.feedback && (
                        <Status tone={a.feedback === "good" ? "success" : "danger"} icon={a.feedback === "good" ? ThumbsUp : ThumbsDown}>
                          {a.feedback === "good" ? "Helpful" : "Not helpful"}
                        </Status>
                      )}
                    </span>
                  </td>
                  <td className="px-4 py-3"><LevelPill level={a.severity} /></td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <button
                      type="button"
                      onClick={(ev) => { ev.stopPropagation(); onOpen(a.id); }}
                      className="inline-flex min-h-9 items-center gap-1.5 rounded-lg px-2.5 text-sm font-medium text-blue-700 hover:bg-blue-50 focus-visible:outline-2 focus-visible:outline-blue-700"
                    >
                      <Eye size={15} aria-hidden="true" /> View
                    </button>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {a.active && a.can_withdraw && (
                      <button
                        type="button"
                        disabled={withdrawing === a.id}
                        onClick={(ev) => { ev.stopPropagation(); void withdraw(a); }}
                        className="inline-flex min-h-9 items-center gap-1.5 rounded-lg px-2.5 text-sm font-medium text-red-700 hover:bg-red-50 focus-visible:outline-2 focus-visible:outline-red-700 disabled:opacity-50"
                      >
                        <Trash2 size={15} aria-hidden="true" /> {withdrawing === a.id ? "Withdrawing…" : "Withdraw"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </section>
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

function Details({ advisory: a, onClose, onChanged }: { advisory: Advisory; onClose: () => void; onChanged: () => void }) {
  const [rating, setRating] = useState<"good" | "poor" | null>(a.feedback);
  const [note, setNote] = useState(a.feedback_note ?? "");
  const [busy, setBusy] = useState<"save" | "withdraw" | null>(null);
  const { notify } = useToast();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const save = async () => {
    if (!rating) return;
    setBusy("save");
    try {
      await reviewAdvisory(a.id, rating, note);
      notify({ tone: "success", title: "Feedback saved", body: a.title });
      onChanged();
    } catch (e) {
      notify({ tone: "alert", title: "Could not save", body: errorMessage(e) });
    } finally {
      setBusy(null);
    }
  };

  const withdraw = async () => {
    if (!window.confirm(`Withdraw "${a.title}"? Citizens stop seeing it straight away.`)) return;
    setBusy("withdraw");
    try {
      await withdrawAdvisory(a.id);
      notify({ tone: "success", title: "Advisory withdrawn", body: a.title });
      onChanged();
    } catch (e) {
      notify({ tone: "alert", title: "Could not withdraw", body: errorMessage(e) });
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-ink/40 p-4" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="advisory-title"
        onClick={(e) => e.stopPropagation()}
        className={cx("flex max-h-[calc(100dvh-2rem)] w-full max-w-3xl flex-col overflow-hidden rounded-3xl border-l-8 bg-surface shadow-lg", LEVELS[a.severity].bar)}
      >
        <header className="flex items-start justify-between gap-4 border-b border-line p-6">
          <div>
            <h2 id="advisory-title" className="text-2xl text-ink">{a.title}</h2>
            <div className="mt-2 flex flex-wrap gap-2">
              <LevelPill level={a.severity} />
              <StatePill a={a} />
            </div>
          </div>
          <button type="button" onClick={onClose} className="grid h-10 w-10 shrink-0 place-items-center rounded-full text-ink-soft hover:bg-paper" aria-label="Close">
            <X size={20} aria-hidden="true" />
          </button>
        </header>

        <div className="grid gap-6 overflow-y-auto p-6 md:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
          <div className="flex flex-col gap-5">
            <div>
              <h3 className="mb-1 text-base font-bold text-ink">Message</h3>
              <p className="whitespace-pre-line text-ink">{a.body}</p>
            </div>
            {a.red_reason && (
              <div className="rounded-xl bg-red-50/70 p-3">
                <h3 className="mb-1 text-sm font-bold text-red-900">Why it was red</h3>
                <p className="text-sm text-red-900">{a.red_reason}</p>
              </div>
            )}
            <dl className="grid gap-4 sm:grid-cols-2">
              <Field label="Released">{fmtDateTime(a.created_at)}</Field>
              <Field label={a.withdrawn_at ? "Withdrawn" : a.active ? "Runs until" : "Ended"}>
                {fmtDate(a.withdrawn_at ?? a.expires_at)}
              </Field>
              <Field label="Audience">{a.audience}</Field>
              <Field label="Reached">{a.reach != null ? `${a.reach} citizens` : "—"}</Field>
              <Field label="Published by">{a.author ?? "—"}</Field>
            </dl>
          </div>

          <div className="flex flex-col gap-4 md:border-l md:border-line md:pl-6">
            <h3 className="text-base font-bold text-ink">Was it a good advisory?</h3>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                aria-pressed={rating === "good"}
                onClick={() => setRating("good")}
                className={cx("flex min-h-11 items-center justify-center gap-2 rounded-xl border-2 text-sm font-semibold", rating === "good" ? "border-green-600 bg-green-50 text-green-900" : "border-line text-ink-soft hover:border-ink/25")}
              >
                <ThumbsUp size={16} aria-hidden="true" /> Helpful
              </button>
              <button
                type="button"
                aria-pressed={rating === "poor"}
                onClick={() => setRating("poor")}
                className={cx("flex min-h-11 items-center justify-center gap-2 rounded-xl border-2 text-sm font-semibold", rating === "poor" ? "border-rose-600 bg-rose-50 text-rose-900" : "border-line text-ink-soft hover:border-ink/25")}
              >
                <ThumbsDown size={16} aria-hidden="true" /> Not helpful
              </button>
            </div>
            <Labelled label="Notes" hint="What worked, what caused confusion, what to do differently.">
              <textarea rows={4} maxLength={1000} value={note} onChange={(e) => setNote(e.target.value)} className={cx(inputCls, "py-3")} />
            </Labelled>
            {a.feedback_at && <p className="text-xs text-ink-muted">Last reviewed {fmtDateTime(a.feedback_at)}</p>}
            <div className="flex flex-wrap gap-2">
              <Btn tone="primary" busy={busy === "save"} disabled={!rating} onClick={() => void save()}>Save feedback</Btn>
              {a.active && a.can_withdraw && (
                <Btn tone="danger" busy={busy === "withdraw"} onClick={() => void withdraw()}>Withdraw</Btn>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
