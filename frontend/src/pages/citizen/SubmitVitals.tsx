import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, CheckCircle2, X } from "lucide-react";
import { Btn, Card, ErrorNote, Loading, PageHeader, SeverityBadge, cx, inputCls } from "../../components/app/ui";
import { fmtDateTime, fromLocalInput, toLocalInput } from "../../lib/format";
import { paths } from "../../lib/routes";
import { useResource } from "../../lib/useResource";
import { errorMessage } from "../../services/api";
import { getMetrics, submitVitals, type Metric, type VitalsResult } from "../../services/health";

const GROUPS: { id: Metric["group"]; title: string }[] = [
  { id: "blood_pressure", title: "Blood pressure" },
  { id: "vitals", title: "Vitals" },
  { id: "other", title: "Other" },
];
const MAX_SYMPTOMS = 12;

function validate(metrics: Metric[], values: Record<string, string>): { vitals: Record<string, number>; errors: Record<string, string> } {
  const vitals: Record<string, number> = {};
  const errors: Record<string, string> = {};
  for (const m of metrics) {
    const raw = values[m.key]?.trim();
    if (!raw) continue;
    const n = Number(raw);
    if (!Number.isFinite(n)) errors[m.key] = "Enter a number";
    else if (n < m.plausible[0] || n > m.plausible[1]) errors[m.key] = `That looks like a typo: expected ${m.plausible[0]}–${m.plausible[1]}`;
    else vitals[m.key] = n;
  }
  if (vitals.systolic !== undefined && vitals.diastolic !== undefined && vitals.diastolic >= vitals.systolic) {
    errors.diastolic = "Diastolic should be lower than systolic. Are they swapped?";
  }
  return { vitals, errors };
}

export function SubmitVitals() {
  const { data: info, error: loadError, reload } = useResource(() => getMetrics(), "metrics");
  const [values, setValues] = useState<Record<string, string>>({});
  const [symptoms, setSymptoms] = useState<string[]>([]);
  const [custom, setCustom] = useState("");
  const [earlier, setEarlier] = useState(false);
  const [measuredAt, setMeasuredAt] = useState(() => toLocalInput(new Date()));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<VitalsResult | null>(null);

  if (loadError) return <ErrorNote message={loadError} onRetry={reload} />;
  if (!info) return <Loading />;
  const byKey = new Map(info.metrics.map((m) => [m.key, m]));

  const toggle = (s: string) =>
    setSymptoms((cur) => (cur.includes(s) ? cur.filter((x) => x !== s) : cur.length < MAX_SYMPTOMS ? [...cur, s] : cur));

  const addCustom = () => {
    const s = custom.trim().toLowerCase().slice(0, 40);
    if (s.length >= 2 && !symptoms.includes(s)) toggle(s);
    setCustom("");
  };

  const reset = () => {
    setValues({});
    setSymptoms([]);
    setEarlier(false);
    setMeasuredAt(toLocalInput(new Date()));
    setErrors({});
    setFormError(null);
    setResult(null);
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const { vitals, errors: found } = validate(info.metrics, values);
    setErrors(found);
    setFormError(null);
    if (Object.keys(found).length) return;
    if (!Object.keys(vitals).length) {
      setFormError("Enter at least one measurement.");
      return;
    }
    setBusy(true);
    try {
      setResult(
        await submitVitals({ vitals, symptoms, measured_at: earlier ? new Date(fromLocalInput(measuredAt)).toISOString() : undefined }),
      );
    } catch (err) {
      setFormError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  // Success replaces the form: a form still on screen invites a second, duplicate entry.
  if (result) {
    const driver = result.driver ? byKey.get(result.driver) : undefined;
    return (
      <>
        <PageHeader title="Reading saved" />
        <Card className="max-w-2xl">
          <div role="status" className="flex gap-4">
            {result.flagged ? (
              <AlertTriangle size={28} className="shrink-0 text-sev-high" aria-hidden="true" />
            ) : (
              <CheckCircle2 size={28} className="shrink-0 text-success" aria-hidden="true" />
            )}
            <div className="flex flex-col gap-2 text-sm">
              <p className="text-lg font-semibold text-ink">
                {result.flagged ? "This reading was flagged" : "All values are within the usual range"}
              </p>
              {result.flagged && (
                <>
                  <p className="flex flex-wrap items-center gap-2">
                    {result.severity && <SeverityBadge severity={result.severity} />}
                    <span className="text-ink">{result.signal ?? `${driver?.label ?? "A value"} is outside its usual range`}</span>
                  </p>
                  <p className="text-ink-soft">
                    {result.reviewed_by_someone
                      ? "Your health centre has been notified and may contact you."
                      : "Nobody is reviewing readings at your centre right now. If you feel unwell, see a doctor."}
                  </p>
                </>
              )}
              <p className="text-ink-soft">{result.basis_note}</p>
              <p className="text-xs text-ink-soft">Measured {fmtDateTime(result.measured_at)}</p>
            </div>
          </div>
          <div className="mt-6 flex flex-wrap gap-2">
            <Link to={paths.citizenHome} className="inline-flex min-h-10 items-center rounded-xl bg-brand px-4 text-sm font-semibold text-on-brand">
              Back to dashboard
            </Link>
            <Link to={paths.history} className="inline-flex min-h-10 items-center rounded-xl border border-line px-4 text-sm font-semibold text-ink">
              See history
            </Link>
            <Btn tone="ghost" onClick={reset}>
              Log another reading
            </Btn>
          </div>
        </Card>
      </>
    );
  }

  return (
    <>
      <PageHeader title="Log vitals" lead="Fill in whatever you measured. Every field is optional, but enter at least one." />
      <form onSubmit={submit} noValidate className="flex max-w-3xl flex-col gap-6">
        {GROUPS.map((group) => (
          <Card key={group.id} title={group.title}>
            <div className="grid gap-4 sm:grid-cols-2">
              {info.metrics
                .filter((m) => m.group === group.id)
                .map((m) => (
                  <label key={m.key} className="flex flex-col gap-1 text-sm">
                    <span className="flex justify-between gap-2 font-medium text-ink">
                      {m.label}
                      <span className="font-normal text-ink-soft">{m.unit}</span>
                    </span>
                    <input
                      inputMode="decimal"
                      value={values[m.key] ?? ""}
                      onChange={(e) => setValues((v) => ({ ...v, [m.key]: e.target.value }))}
                      aria-invalid={errors[m.key] ? true : undefined}
                      aria-describedby={`${m.key}-hint`}
                      className={cx(inputCls, errors[m.key] && "border-danger")}
                    />
                    <span id={`${m.key}-hint`} className={cx("text-xs", errors[m.key] ? "text-danger" : "text-ink-soft")}>
                      {errors[m.key] ?? (m.normal ? `Normal: ${m.normal[0]}–${m.normal[1]} ${m.unit}` : "No normal range; tracked for your record")}
                    </span>
                  </label>
                ))}
            </div>
          </Card>
        ))}

        <Card title="Symptoms (optional)">
          <div className="flex flex-wrap gap-2">
            {[...info.common_symptoms, ...symptoms.filter((s) => !info.common_symptoms.includes(s))].map((s) => {
              const on = symptoms.includes(s);
              return (
                <button
                  key={s}
                  type="button"
                  aria-pressed={on}
                  onClick={() => toggle(s)}
                  className={cx(
                    "inline-flex min-h-9 items-center gap-1 rounded-full border px-3 text-sm capitalize",
                    on ? "border-brand bg-brand-soft text-brand" : "border-line text-ink-soft hover:text-ink",
                  )}
                >
                  {s}
                  {on && <X size={14} aria-hidden="true" />}
                </button>
              );
            })}
          </div>
          <div className="mt-3 flex max-w-sm gap-2">
            <input
              value={custom}
              maxLength={40}
              onChange={(e) => setCustom(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addCustom();
                }
              }}
              placeholder="Something else"
              aria-label="Add another symptom"
              className={inputCls}
            />
            <Btn onClick={addCustom} disabled={custom.trim().length < 2 || symptoms.length >= MAX_SYMPTOMS}>
              Add
            </Btn>
          </div>
        </Card>

        <Card>
          <label className="flex items-center gap-2 text-sm text-ink">
            <input type="checkbox" checked={earlier} onChange={(e) => setEarlier(e.target.checked)} />I measured this earlier
          </label>
          {earlier && (
            <input
              type="datetime-local"
              value={measuredAt}
              max={toLocalInput(new Date())}
              min={toLocalInput(new Date(Date.now() - 30 * 86400_000))}
              onChange={(e) => setMeasuredAt(e.target.value)}
              aria-label="When it was measured (India time)"
              className={cx(inputCls, "mt-3 max-w-xs")}
            />
          )}
        </Card>

        {formError && <ErrorNote message={formError} />}
        <div>
          <Btn tone="primary" type="submit" busy={busy}>
            Save reading
          </Btn>
        </div>
      </form>
    </>
  );
}
