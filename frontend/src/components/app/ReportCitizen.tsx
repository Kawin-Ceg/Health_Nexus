import { useState, type FormEvent } from "react";
import { CalendarX } from "lucide-react";
import { useResource } from "../../lib/useResource";
import { raiseConcern } from "../../services/account";
import { errorMessage } from "../../services/api";
import { getMissedVisits } from "../../services/phc";
import { useToast } from "./Toaster";
import { Btn, Card, Labelled, Loading, cx, inputCls } from "./ui";

type Kind = "citizen_missed_visits" | "citizen_conduct";

export function ReportCitizen({ citizenId, name, onClose }: { citizenId: string; name: string; onClose: () => void }) {
  const evidence = useResource((s) => getMissedVisits(citizenId, s), `missed-${citizenId}`);
  const [kind, setKind] = useState<Kind>("citizen_missed_visits");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { notify } = useToast();
  const e = evidence.data;
  const blocked = kind === "citizen_missed_visits" && !e?.eligible;

  const submit = async (ev: FormEvent) => {
    ev.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const c = await raiseConcern(kind, text, citizenId);
      notify({ tone: "success", title: "Complaint sent to your district admin", body: c.ticket_ref });
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title={`Report a problem with ${name}`} className="mb-6">
      <form onSubmit={submit} className="flex flex-col gap-4 text-sm">
        <div className="flex flex-wrap gap-2">
          {(
            [
              ["citizen_missed_visits", "Keeps missing visits"],
              ["citizen_conduct", "Behaviour during a visit"],
            ] as [Kind, string][]
          ).map(([k, label]) => (
            <button
              key={k}
              type="button"
              aria-pressed={kind === k}
              onClick={() => setKind(k)}
              className={cx("min-h-10 rounded-full border px-4 font-medium", kind === k ? "border-ink bg-ink text-paper" : "border-line bg-surface text-ink hover:border-ink/40")}
            >
              {label}
            </button>
          ))}
        </div>

        {kind === "citizen_missed_visits" &&
          (!e ? (
            <Loading />
          ) : (
            <div className={cx("rounded-xl p-3", e.eligible ? "bg-red-50 text-red-900" : "bg-paper text-ink")}>
              <p className="flex items-center gap-2 font-semibold">
                <CalendarX size={16} aria-hidden="true" /> {e.unexplained} unexplained of {e.missed} missed visits in the last {e.window_days} days
              </p>
              <p className="mt-1">
                {e.eligible
                  ? "The record supports a complaint. These visits will be attached as evidence."
                  : `A complaint needs ${e.threshold} missed visits without a reason. The citizen can explain a missed visit from their app, and explained visits do not count.`}
              </p>
              {e.visits.length > 0 && (
                <ul className="mt-2 flex flex-col gap-1">
                  {e.visits.map((v) => (
                    <li key={v.at} className="text-xs">
                      {v.when}
                      {v.location ? ` · ${v.location}` : ""} · {v.explanation ? `explained: "${v.explanation}"` : "no reason given"}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}

        <Labelled label="What happened" hint={`${text.trim().length}/2000, at least 10 characters`}>
          <textarea rows={3} maxLength={2000} value={text} onChange={(ev) => setText(ev.target.value)} className={cx(inputCls, "py-2")} />
        </Labelled>
        {error && <p className="text-danger">{error}</p>}
        <div className="flex gap-2">
          <Btn tone="primary" type="submit" busy={busy} disabled={blocked || text.trim().length < 10}>Send to admin</Btn>
          <Btn tone="ghost" onClick={onClose}>Cancel</Btn>
        </div>
      </form>
    </Card>
  );
}
