import { useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { Megaphone } from "lucide-react";
import { Btn, Card, Empty, ErrorNote, Labelled, Loading, PageHeader, cx, inputCls } from "../components/app/ui";
import { useToast } from "../components/app/Toaster";
import { useAuth } from "../context/AuthContext";
import { fmtDate, fmtDateTime } from "../lib/format";
import { useResource } from "../lib/useResource";
import { getCentres } from "../services/admin";
import { listAdvisories, publishAdvisory, withdrawAdvisory, type Advisory, type AdvisoryInput, type AdvisoryScope } from "../services/advisories";
import { errorMessage } from "../services/api";

const TONE: Record<Advisory["severity"], string> = {
  high: "border-l-sev-high",
  medium: "border-l-sev-moderate",
  low: "border-l-line",
};

export function Advisories() {
  const { user } = useAuth();
  const admin = user?.role === "admin";
  const [showEnded, setShowEnded] = useState(false);
  const list = useResource((s) => listAdvisories(showEnded, s), `advisories-${showEnded}`);

  return (
    <>
      <PageHeader
        title="Community advisories"
        lead={
          admin
            ? "Notices for every citizen in a district or across the state. They appear on citizens' Alerts page until they expire or you withdraw them."
            : "Notices for the citizens registered at your health centre. They appear on their Alerts page until they expire or you withdraw them."
        }
      />
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
        <Compose admin={admin} onPublished={list.reload} />
        <section aria-labelledby="advisory-list">
          <div className="mb-3 flex items-center justify-between gap-2">
            <h2 id="advisory-list" className="text-xl text-ink">{showEnded ? "All advisories" : "Running now"}</h2>
            <label className="flex items-center gap-2 text-sm text-ink-soft">
              <input type="checkbox" checked={showEnded} onChange={(e) => setShowEnded(e.target.checked)} /> Show ended
            </label>
          </div>
          {list.error && <ErrorNote message={list.error} onRetry={list.reload} />}
          {!list.data ? (
            !list.error && <Loading />
          ) : list.data.length === 0 ? (
            <Empty title="No advisories" />
          ) : (
            <ul className="flex flex-col gap-3">
              {list.data.map((a) => (
                <AdvisoryCard key={a.id} advisory={a} onChanged={list.reload} />
              ))}
            </ul>
          )}
        </section>
      </div>
    </>
  );
}

function AdvisoryCard({ advisory: a, onChanged }: { advisory: Advisory; onChanged: () => void }) {
  const [busy, setBusy] = useState(false);
  const { notify } = useToast();

  const withdraw = async () => {
    if (!window.confirm(`Withdraw "${a.title}"? Citizens stop seeing it straight away.`)) return;
    setBusy(true);
    try {
      await withdrawAdvisory(a.id);
      notify({ tone: "success", title: "Advisory withdrawn", body: a.title });
      onChanged();
    } catch (e) {
      notify({ tone: "alert", title: "Could not withdraw", body: errorMessage(e) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <li className={cx("rounded-2xl border border-line border-l-4 bg-surface p-4 text-sm", TONE[a.severity], !a.active && "opacity-70")}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-semibold text-ink">{a.title}</p>
          <p className="text-xs text-ink-soft">
            {a.audience}
            {a.reach != null && ` · reaches ${a.reach} citizen${a.reach === 1 ? "" : "s"}`}
          </p>
        </div>
        {a.active && a.can_withdraw && (
          <Btn tone="ghost" busy={busy} onClick={() => void withdraw()}>Withdraw</Btn>
        )}
      </div>
      <p className="mt-2 whitespace-pre-line text-ink">{a.body}</p>
      <p className="mt-2 text-xs text-ink-muted">
        {a.author ? `${a.author}, ` : ""}
        {fmtDateTime(a.created_at)} ·{" "}
        {a.withdrawn_at ? `withdrawn ${fmtDate(a.withdrawn_at)}` : a.active ? `until ${fmtDate(a.expires_at)}` : `ended ${fmtDate(a.expires_at)}`}
      </p>
    </li>
  );
}

function Compose({ admin, onPublished }: { admin: boolean; onPublished: () => void }) {
  const districts = useResource((s) => (admin ? getCentres({ limit: 1 }, s).then((r) => r.districts) : Promise.resolve([])), `districts-${admin}`);
  const [params, setParams] = useSearchParams();
  const clusterId = params.get("cluster");
  const [scope, setScope] = useState<AdvisoryScope>(admin ? "district" : "centre");
  const [district, setDistrict] = useState("");
  const [title, setTitle] = useState(params.get("title") ?? "");
  const [body, setBody] = useState(params.get("body") ?? "");
  const [severity, setSeverity] = useState<Advisory["severity"]>("medium");
  const [days, setDays] = useState(14);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { notify } = useToast();

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const input: AdvisoryInput = {
        scope,
        title,
        body,
        severity,
        days,
        ...(scope === "district" ? { district } : {}),
        ...(clusterId ? { cluster_id: clusterId } : {}),
      };
      const made = await publishAdvisory(input);
      notify({ tone: "success", title: "Advisory published", body: `${made.audience}: ${made.reach ?? 0} citizens` });
      setTitle("");
      setBody("");
      if (clusterId) setParams({}, { replace: true });
      onPublished();
    } catch (e2) {
      setError(errorMessage(e2));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title={<span className="flex items-center gap-2"><Megaphone size={20} aria-hidden="true" /> New advisory</span>}>
      <form onSubmit={submit} className="flex flex-col gap-4">
        {clusterId && <p className="rounded-2xl bg-paper p-3 text-sm text-ink-soft">Drafted from an outbreak signal. Edit it before publishing.</p>}
        {admin && (
          <div className="grid gap-4 sm:grid-cols-2">
            <Labelled label="Who sees it">
              <select value={scope} onChange={(e) => setScope(e.target.value as AdvisoryScope)} className={inputCls}>
                <option value="district">One district</option>
                <option value="state">Everyone in the state</option>
              </select>
            </Labelled>
            {scope === "district" && (
              <Labelled label="District">
                <select required value={district} onChange={(e) => setDistrict(e.target.value)} className={inputCls}>
                  <option value="">Choose…</option>
                  {districts.data?.map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </Labelled>
            )}
          </div>
        )}
        <Labelled label="Title">
          <input required minLength={4} maxLength={120} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Dengue precautions" className={inputCls} />
        </Labelled>
        <Labelled label="Message" hint={`${body.length}/2000. Plain words: what is happening and what people should do.`}>
          <textarea
            required
            minLength={10}
            maxLength={2000}
            rows={5}
            value={body}
            onChange={(e) => setBody(e.target.value)}
            className={cx(inputCls, "py-3")}
          />
        </Labelled>
        <div className="grid gap-4 sm:grid-cols-2">
          <Labelled label="How urgent">
            <select value={severity} onChange={(e) => setSeverity(e.target.value as Advisory["severity"])} className={inputCls}>
              <option value="low">For information</option>
              <option value="medium">Take precautions</option>
              <option value="high">Act now</option>
            </select>
          </Labelled>
          <Labelled label="Show for">
            <select value={days} onChange={(e) => setDays(Number(e.target.value))} className={inputCls}>
              {[3, 7, 14, 30, 60, 90].map((d) => (
                <option key={d} value={d}>{d} days</option>
              ))}
            </select>
          </Labelled>
        </div>
        {error && <p className="text-sm text-danger">{error}</p>}
        <div>
          <Btn tone="primary" type="submit" busy={busy}>Publish</Btn>
        </div>
      </form>
    </Card>
  );
}
