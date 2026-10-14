import { useState, type FormEvent, type ReactNode } from "react";
import { FileText, Upload } from "lucide-react";
import { fmtDateTime } from "../../lib/format";
import { errorMessage } from "../../services/api";
import {
  DOCUMENT_TYPES,
  decideDocument,
  openDocument,
  removeDocument,
  uploadDocument,
  type DocumentStatus,
  type DocumentType,
  type VerificationDocument,
} from "../../services/documents";
import { useToast } from "./Toaster";
import { Btn, cx, inputCls } from "./ui";

const STATUS: Record<DocumentStatus, { label: string; cls: string }> = {
  pending: { label: "Waiting for review", cls: "bg-paper text-ink-soft" },
  auto_passed: { label: "Checks passed", cls: "bg-success-soft text-success" },
  flagged: { label: "Needs a closer look", cls: "bg-warn/15 text-warn" },
  accepted: { label: "Accepted", cls: "bg-success-soft text-success" },
  rejected: { label: "Rejected", cls: "bg-danger-soft text-danger" },
};

const typeLabel = (t: DocumentType) => DOCUMENT_TYPES.find((d) => d.value === t)?.label ?? t;

export function DocumentStatusChip({ status }: { status: DocumentStatus }) {
  return <span className={cx("rounded-full px-2 py-0.5 text-xs font-semibold", STATUS[status].cls)}>{STATUS[status].label}</span>;
}

function Item({ doc, children, showNotes }: { doc: VerificationDocument; children?: ReactNode; showNotes: boolean }) {
  return (
    <li className="rounded-2xl border border-line bg-surface p-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <FileText size={16} className="shrink-0 text-ink-muted" aria-hidden="true" />
        <span className="font-medium text-ink">{typeLabel(doc.document_type)}</span>
        <DocumentStatusChip status={doc.status} />
        <span className="ml-auto text-xs text-ink-muted">
          {doc.original_filename ?? "file"} · {Math.ceil(doc.size_bytes / 1024)} KB · {fmtDateTime(doc.uploaded_at)}
        </span>
      </div>
      {showNotes && doc.check_notes && <p className="mt-2 text-xs text-ink-soft">{doc.check_notes}</p>}
      {children}
    </li>
  );
}

export function ApplicantDocuments({ docs, onChanged }: { docs: VerificationDocument[]; onChanged: () => void }) {
  const [type, setType] = useState<DocumentType>("employee_id_card");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { notify } = useToast();

  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      await uploadDocument(type, file);
      setFile(null);
      e.currentTarget.reset();
      onChanged();
    } catch (e2) {
      setError(errorMessage(e2));
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id: string) => {
    try {
      await removeDocument(id);
      onChanged();
    } catch (e) {
      notify({ tone: "alert", title: "Could not remove", body: errorMessage(e) });
    }
  };

  return (
    <div className="flex flex-col gap-4 text-left">
      <form onSubmit={submit} className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-ink">Document</span>
          <select value={type} onChange={(e) => setType(e.target.value as DocumentType)} className={cx(inputCls, "w-auto!")}>
            {DOCUMENT_TYPES.map((d) => (
              <option key={d.value} value={d.value}>{d.label}</option>
            ))}
          </select>
        </label>
        <label className="flex min-w-0 flex-1 flex-col gap-1 text-sm">
          <span className="font-medium text-ink">File (JPEG, PNG or PDF, up to 5 MB)</span>
          <input type="file" accept="image/jpeg,image/png,application/pdf" required onChange={(e) => setFile(e.target.files?.[0] ?? null)} className="text-sm" />
        </label>
        <Btn tone="primary" type="submit" busy={busy} disabled={!file}>
          <Upload size={16} aria-hidden="true" /> Upload
        </Btn>
      </form>
      {error && <p className="text-sm text-danger">{error}</p>}
      {docs.length > 0 && (
        <ul className="flex flex-col gap-2">
          {docs.map((d) => (
            <Item key={d.id} doc={d} showNotes={false}>
              <div className="mt-2 text-right">
                <Btn tone="ghost" onClick={() => void remove(d.id)}>Remove</Btn>
              </div>
            </Item>
          ))}
        </ul>
      )}
    </div>
  );
}

export function ReviewDocuments({ applicationId, docs }: { applicationId: string; docs: VerificationDocument[] }) {
  const [list, setList] = useState(docs);
  if (list.length === 0) {
    return <p className="text-sm text-warn">No documents uploaded. You are deciding from the typed details alone.</p>;
  }
  return (
    <ul className="flex flex-col gap-2">
      {list.map((d) => (
        <ReviewItem key={d.id} applicationId={applicationId} doc={d} onDecided={(next) => setList(list.map((x) => (x.id === next.id ? next : x)))} />
      ))}
    </ul>
  );
}

function ReviewItem({ applicationId, doc, onDecided }: { applicationId: string; doc: VerificationDocument; onDecided: (d: VerificationDocument) => void }) {
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const { notify } = useToast();

  const decide = async (accept: boolean) => {
    setBusy(true);
    try {
      onDecided(await decideDocument(applicationId, doc.id, accept, reason));
      setRejecting(false);
    } catch (e) {
      notify({ tone: "alert", title: "Could not save", body: errorMessage(e) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Item doc={doc} showNotes>
      {doc.extracted_registration_no && <p className="mt-1 text-xs text-success">Employee ID found in the document: {doc.extracted_registration_no}</p>}
      <div className="mt-2 flex flex-wrap items-center justify-end gap-2">
        <Btn tone="ghost" onClick={() => void openDocument(applicationId, doc.id).catch((e) => notify({ tone: "alert", title: "Could not open", body: errorMessage(e) }))}>
          View
        </Btn>
        {doc.status !== "accepted" && <Btn busy={busy && !rejecting} onClick={() => void decide(true)}>Accept</Btn>}
        {doc.status !== "rejected" && !rejecting && <Btn tone="ghost" onClick={() => setRejecting(true)}>Reject</Btn>}
      </div>
      {rejecting && (
        <div className="mt-2 flex flex-wrap gap-2">
          <input className={cx(inputCls, "flex-1")} autoFocus placeholder="Why?" value={reason} maxLength={500} onChange={(e) => setReason(e.target.value)} />
          <Btn tone="danger" busy={busy} disabled={reason.trim().length < 3} onClick={() => void decide(false)}>Reject</Btn>
          <Btn tone="ghost" onClick={() => setRejecting(false)}>Cancel</Btn>
        </div>
      )}
    </Item>
  );
}
