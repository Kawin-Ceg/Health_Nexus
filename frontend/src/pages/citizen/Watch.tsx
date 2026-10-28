import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, CheckCircle2, Moon, RefreshCw, Sun, Sunrise, Sunset, Watch as WatchIcon } from "lucide-react";
import { Btn, Card, ErrorNote, Loading, PageHeader, SeverityBadge, cx, inputCls } from "../../components/app/ui";
import { useToast } from "../../components/app/Toaster";
import { useLabel } from "../../i18n";
import { fmtDateTime } from "../../lib/format";
import { paths } from "../../lib/routes";
import { useResource } from "../../lib/useResource";
import { errorMessage } from "../../services/api";
import {
  connectWatch,
  disconnectWatch,
  getMetrics,
  getWatch,
  syncWatch,
  type VitalsResult,
  type WatchSlotKey,
  type WatchState,
} from "../../services/health";

const ORDER = ["heart_rate", "spo2", "respiratory_rate", "temperature_c", "systolic", "diastolic", "glucose_mg_dl", "weight_kg"];
const order = (vitals: Record<string, number>) =>
  Object.entries(vitals).sort(([a], [b]) => (ORDER.indexOf(a) + 99) % 99 - (ORDER.indexOf(b) + 99) % 99);

const SLOT_ICON: Record<WatchSlotKey, typeof Sun> = { morning: Sunrise, afternoon: Sun, evening: Sunset, night: Moon };

export function Watch() {
  const res = useResource((s) => Promise.all([getWatch(s), getMetrics()]), "watch");
  const [state, setState] = useState<WatchState | null>(null);
  const [last, setLast] = useState<{ reading: VitalsResult; already: boolean } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const label = useLabel();
  const { notify } = useToast();

  if (res.error) return <ErrorNote message={res.error} onRetry={res.reload} />;
  if (!res.data) return <Loading />;
  const watch = state ?? res.data[0];
  const units = new Map(res.data[1].metrics.map((m) => [m.key, m]));

  const fetchNow = async () => {
    setBusy(true);
    setError(null);
    try {
      const out = await syncWatch();
      setLast({ reading: out.reading, already: out.already_synced });
      setState(await getWatch());
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const disconnect = async () => {
    if (!window.confirm("Disconnect your smartwatch? Readings already synced stay in your history.")) return;
    setState(await disconnectWatch());
    setLast(null);
    notify({ tone: "info", title: "Smartwatch disconnected" });
  };

  if (!watch.connected) return <Connect onConnected={setState} />;

  const current = watch.slots.find((s) => s.key === watch.current_slot)!;
  const done = watch.slots.filter((s) => s.reading_id).length;

  return (
    <>
      <PageHeader
        title="Smartwatch"
        lead={`${watch.brand ?? "Your watch"} is connected. Fetch a reading in each part of the day: up to four a day.`}
        actions={<Btn tone="ghost" onClick={() => void disconnect()}>Disconnect</Btn>}
      />

      <section className="mb-6 flex flex-wrap items-center gap-6 rounded-3xl border border-line bg-surface p-6 md:p-8">
        <span className="grid size-16 place-items-center rounded-full bg-lime text-olive">
          <WatchIcon size={30} aria-hidden="true" />
        </span>
        <div className="min-w-56 flex-1">
          <p className="text-sm font-semibold uppercase tracking-[0.06em] text-ink-muted">Now: {current.label.toLowerCase()} ({current.hours})</p>
          <p className="mt-1 font-display text-2xl text-ink">
            {current.reading_id ? `This ${current.label.toLowerCase()}'s reading is in. Next one in the next part of the day.` : `Ready to fetch your ${current.label.toLowerCase()} reading.`}
          </p>
          <p className="mt-1 text-sm text-ink-soft">{done} of 4 synced today.</p>
        </div>
        <Btn tone="primary" busy={busy} onClick={() => void fetchNow()}>
          <RefreshCw size={16} aria-hidden="true" /> {current.reading_id ? "Fetch again" : "Fetch from watch"}
        </Btn>
      </section>
      {error && <div className="mb-6"><ErrorNote message={error} /></div>}

      {last && <Result reading={last.reading} already={last.already} units={units} label={label} />}

      <h2 className="mb-3 text-xl text-ink">Today</h2>
      <ol className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {watch.slots.map((s) => {
          const Icon = SLOT_ICON[s.key];
          const now = s.key === watch.current_slot;
          return (
            <li key={s.key} className={cx("rounded-3xl border bg-surface p-4 text-sm", now ? "border-ink" : "border-line")}>
              <p className="flex items-center gap-2 font-semibold text-ink">
                <Icon size={16} aria-hidden="true" /> {s.label}
                <span className="ml-auto text-xs font-normal text-ink-muted">{s.hours}</span>
              </p>
              {s.vitals ? (
                <ul className="mt-3 flex flex-col gap-1 text-ink-soft">
                  {order(s.vitals).map(([k, v]) => (
                    <li key={k} className="flex justify-between gap-2">
                      <span>{label("vital", k, units.get(k)?.label)}</span>
                      <span className="tabular-nums text-ink">{v} {units.get(k)?.unit}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-3 text-ink-muted">{now ? "Not fetched yet" : "No reading"}</p>
              )}
            </li>
          );
        })}
      </ol>
      <div role="note" className="mt-8 flex gap-3 rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950">
        <AlertTriangle size={20} className="mt-0.5 shrink-0 text-amber-700" aria-hidden="true" />
        <div className="flex flex-col gap-1">
          <p className="font-semibold">Please note</p>
          <ul className="list-disc space-y-1 pl-4">
            <li>A watch reading is not a diagnosis. If you feel unwell, see a doctor. In an emergency, call 108.</li>
            <li>Blood pressure, blood sugar and weight from a watch are estimates. Your health worker's examination is more accurate.</li>
            <li>Every reading is kept in your <Link to={paths.history} className="font-semibold underline">history</Link>.</li>
          </ul>
        </div>
      </div>
    </>
  );
}

function Result({ reading: r, already, units, label }: {
  reading: VitalsResult;
  already: boolean;
  units: Map<string, { label: string; unit: string }>;
  label: ReturnType<typeof useLabel>;
}) {
  return (
    <Card className="mb-6" title={already ? "Already synced in this part of the day" : "Reading synced"}>
      <div className="flex gap-4">
        {r.flagged ? <AlertTriangle size={26} className="shrink-0 text-sev-high" aria-hidden="true" /> : <CheckCircle2 size={26} className="shrink-0 text-success" aria-hidden="true" />}
        <div className="flex flex-1 flex-col gap-2 text-sm">
          <p className="flex flex-wrap items-center gap-2 font-semibold text-ink">
            {r.flagged ? "This reading was flagged" : "All values are within your usual range"}
            {r.severity && <SeverityBadge severity={r.severity} />}
          </p>
          {r.signal && <p className="text-ink">{r.signal}</p>}
          <p className="flex flex-wrap gap-x-4 gap-y-1 text-ink-soft">
            {order(r.vitals).map(([k, v]) => (
              <span key={k}>
                {label("vital", k, units.get(k)?.label)}: <span className="tabular-nums text-ink">{v} {units.get(k)?.unit}</span>
              </span>
            ))}
          </p>
          <p className="text-xs text-ink-muted">Measured {fmtDateTime(r.measured_at)}</p>
        </div>
      </div>
    </Card>
  );
}

function Connect({ onConnected }: { onConnected: (s: WatchState) => void }) {
  const [brand, setBrand] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      onConnected(await connectWatch(brand.trim()));
    } catch (e2) {
      setError(errorMessage(e2));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader title="Smartwatch" lead="Your readings come from your smartwatch. Connect it to start." />
      <Card className="max-w-xl" title="Connect your smartwatch">
        <form onSubmit={submit} className="flex flex-col gap-4">
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-ink">Brand</span>
            <input required minLength={2} maxLength={60} value={brand} onChange={(e) => setBrand(e.target.value)} placeholder="Noise, boAt, Fitbit, Apple…" className={inputCls} />
          </label>
          {error && <p className="text-sm text-danger">{error}</p>}
          <div>
            <Btn tone="primary" type="submit" busy={busy} disabled={brand.trim().length < 2}>
              <WatchIcon size={16} aria-hidden="true" /> Connect
            </Btn>
          </div>
          <p className="text-xs text-ink-muted">
            No watch? Your health worker can record your vitals when they examine you, and those readings appear in your
            history too.
          </p>
        </form>
      </Card>
    </>
  );
}
