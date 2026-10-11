import { useState } from "react";
import { Btn, Card, Empty, ErrorNote, Loading, PageHeader, Tabs, cx, inputCls } from "../../components/app/ui";
import { fmtAgo, fmtDateTime } from "../../lib/format";
import { useResource } from "../../lib/useResource";
import { errorMessage } from "../../services/api";
import { getConcerns, updateConcern, type ConcernCategory, type ConcernItem, type ConcernStatus } from "../../services/admin";

const STATUS_LABEL: Record<ConcernStatus, string> = { open: "Open", in_review: "In review", resolved: "Resolved", rejected: "Declined" };
const CATEGORY_LABEL: Record<ConcernCategory, string> = {
  data_misuse: "Data misuse",
  incorrect_diagnosis_flag: "Incorrect flag",
  harassment: "Harassment",
  access_request: "Access request",
  other: "Other",
};

export function Concerns() {
  const [status, setStatus] = useState<ConcernStatus | "">("open");
  const res = useResource((s) => getConcerns({ status }, s), status);
  const d = res.data;

  return (
    <>
      <PageHeader title="Support concerns" lead="Concerns raised from Settings → Support. Your note is shown back to the person who raised it." />
      {d && (
        <Tabs
          label="Status"
          value={status || "all"}
          onChange={(v) => setStatus(v === "all" ? "" : v)}
          tabs={[
            ...(Object.keys(STATUS_LABEL) as ConcernStatus[]).map((s) => ({ id: s, label: `${STATUS_LABEL[s]} (${d.counts[s]})` })),
            { id: "all" as const, label: "All" },
          ]}
        />
      )}
      {res.error && <ErrorNote message={res.error} onRetry={res.reload} />}
      {!d ? (
        !res.error && <Loading />
      ) : d.items.length === 0 ? (
        <Empty title="Nothing here" />
      ) : (
        <div className={cx("flex flex-col gap-3", res.loading && "opacity-60")}>
          {d.items.map((c) => (
            <ConcernCard key={c.id} concern={c} onChanged={res.reload} />
          ))}
        </div>
      )}
    </>
  );
}

function ConcernCard({ concern: c, onChanged }: { concern: ConcernItem; onChanged: () => void }) {
  const [note, setNote] = useState(c.admin_note ?? "");
  const [busy, setBusy] = useState<ConcernStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  const move = async (status: ConcernStatus) => {
    setBusy(status);
    setError(null);
    try {
      await updateConcern(c.id, { status, admin_note: note });
      onChanged();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(null);
    }
  };
  const closed = c.status === "resolved" || c.status === "rejected";

  return (
    <Card
      title={
        <span className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-sm">{c.ticket_ref}</span>
          <span className="rounded-full bg-paper-raised px-2 py-0.5 text-xs font-medium text-ink-soft">{CATEGORY_LABEL[c.category]}</span>
        </span>
      }
      aside={<span className="text-xs text-ink-soft">{STATUS_LABEL[c.status]} · raised {fmtAgo(c.created_at)}</span>}
    >
      <p className="whitespace-pre-wrap text-sm text-ink">{c.description}</p>
      <p className="mt-2 text-xs text-ink-soft">
        {c.raised_by} ({c.raised_by_email}, {c.raised_by_role === "user" ? "citizen" : c.raised_by_role.replace("_", " ")})
        {c.handled_by && ` · handled by ${c.handled_by}`}
        {c.resolved_at && ` · closed ${fmtDateTime(c.resolved_at)}`}
      </p>
      <label className="mt-4 flex flex-col gap-1 text-sm">
        <span className="font-medium text-ink">Note to the person</span>
        <textarea className={cx(inputCls, "min-h-20 py-2")} value={note} maxLength={2000} onChange={(e) => setNote(e.target.value)} />
      </label>
      <div className="mt-3 flex flex-wrap gap-2">
        {c.status === "open" && <Btn busy={busy === "in_review"} onClick={() => move("in_review")}>Start review</Btn>}
        {!closed && <Btn tone="primary" busy={busy === "resolved"} disabled={!note.trim()} onClick={() => move("resolved")}>Resolve</Btn>}
        {!closed && <Btn tone="ghost" busy={busy === "rejected"} disabled={!note.trim()} onClick={() => move("rejected")}>Decline</Btn>}
        {closed && <Btn busy={busy === "open"} onClick={() => move("open")}>Reopen</Btn>}
      </div>
      {error && <div className="mt-3"><ErrorNote message={error} /></div>}
    </Card>
  );
}
