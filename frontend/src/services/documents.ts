import { api } from "./api";

export type DocumentType = "employee_id_card" | "appointment_order" | "registration_certificate";
export type DocumentStatus = "pending" | "auto_passed" | "flagged" | "rejected" | "accepted";

export interface VerificationDocument {
  id: string;
  document_type: DocumentType;
  original_filename: string | null;
  content_type: string;
  size_bytes: number;
  status: DocumentStatus;
  check_notes: string | null;
  extracted_registration_no: string | null;
  tamper_score: number | null;
  uploaded_at: string;
  checked_at: string | null;
  opened: boolean;
}

export const DOCUMENT_TYPES: { value: DocumentType; label: string }[] = [
  { value: "employee_id_card", label: "Employee ID card" },
  { value: "appointment_order", label: "Appointment order" },
  { value: "registration_certificate", label: "Registration certificate" },
];

export const myDocuments = (signal?: AbortSignal) =>
  api.get<VerificationDocument[]>("/phc-application/documents", { signal }).then((r) => r.data);

export function uploadDocument(type: DocumentType, file: File) {
  const form = new FormData();
  form.append("document_type", type);
  form.append("file", file);
  return api.post<VerificationDocument>("/phc-application/documents", form).then((r) => r.data);
}

export const removeDocument = (id: string) => api.delete(`/phc-application/documents/${id}`);

export async function openDocument(applicationId: string, id: string) {
  const r = await api.get<Blob>(`/admin/applications/${applicationId}/documents/${id}/file`, { responseType: "blob" });
  const url = URL.createObjectURL(r.data);
  window.open(url, "_blank", "noopener");
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

export const decideDocument = (applicationId: string, id: string, accept: boolean, reason?: string) =>
  api
    .post<VerificationDocument>(`/admin/applications/${applicationId}/documents/${id}/decision`, { accept, reason: reason || undefined })
    .then((r) => r.data);
