import { api } from "./api";

export type AdvisoryScope = "centre" | "district" | "state";

export interface Advisory {
  id: string;
  scope: AdvisoryScope;
  audience: string;
  title: string;
  body: string;
  severity: "low" | "medium" | "high";
  author: string | null;
  created_at: string;
  expires_at: string;
  withdrawn_at: string | null;
  active: boolean;
  reach: number | null;
  can_withdraw: boolean;
}

export interface AdvisoryInput {
  scope: AdvisoryScope;
  district?: string;
  title: string;
  body: string;
  severity: Advisory["severity"];
  days: number;
  cluster_id?: string;
}

export const listAdvisories = (includeEnded: boolean, signal?: AbortSignal) =>
  api.get<{ items: Advisory[] }>("/advisories", { params: { include_ended: includeEnded }, signal }).then((r) => r.data.items);
export const publishAdvisory = (input: AdvisoryInput) => api.post<Advisory>("/advisories", input).then((r) => r.data);
export const withdrawAdvisory = (id: string) => api.post<Advisory>(`/advisories/${id}/withdraw`).then((r) => r.data);
