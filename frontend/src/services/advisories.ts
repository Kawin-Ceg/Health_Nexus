import { api } from "./api";

export type AdvisoryScope = "centre" | "area" | "district" | "state";

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
  area: string | null;
  radius_km: number | null;
  red_reason: string | null;
  feedback: "good" | "poor" | null;
  feedback_note: string | null;
  feedback_at: string | null;
}

export interface RedCheck {
  allowed: boolean;
  message: string;
  checks: { label: string; value: string; met: boolean }[];
}

export interface AdvisoryInput {
  scope: AdvisoryScope;
  district?: string;
  title: string;
  body: string;
  severity: Advisory["severity"];
  days: number;
  cluster_id?: string;
  red_reason?: string;
  phc_id?: string;
  area?: string;
  radius_km?: number;
}

export type Target = Pick<AdvisoryInput, "scope" | "district" | "phc_id" | "area" | "radius_km">;

export interface Targets {
  district: string | null;
  centres: { id: string; name: string; block: string | null; located: boolean; citizens: number }[];
  localities: { name: string; citizens: number }[];
  pincodes: { name: string; citizens: number }[];
}

export const getTargets = (signal?: AbortSignal) => api.get<Targets>("/advisories/targets", { signal }).then((r) => r.data);
export const previewReach = (target: Target, signal?: AbortSignal) =>
  api.post<{ citizens: number; registered: number }>("/advisories/reach", target, { signal }).then((r) => r.data);

export const listAdvisories = (includeEnded: boolean, signal?: AbortSignal) =>
  api.get<{ items: Advisory[] }>("/advisories", { params: { include_ended: includeEnded }, signal }).then((r) => r.data.items);
export const publishAdvisory = (input: AdvisoryInput) => api.post<Advisory>("/advisories", input).then((r) => r.data);
export const withdrawAdvisory = (id: string) => api.post<Advisory>(`/advisories/${id}/withdraw`).then((r) => r.data);
export const checkRed = (clusterId?: string | null) =>
  api.get<RedCheck>("/advisories/red-check", { params: clusterId ? { cluster_id: clusterId } : {} }).then((r) => r.data);
export const reviewAdvisory = (id: string, rating: "good" | "poor", note: string) =>
  api.post<Advisory>(`/advisories/${id}/feedback`, { rating, note }).then((r) => r.data);
