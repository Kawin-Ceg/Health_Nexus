import { api } from "./api";

export interface Cluster {
  id: string;
  syndrome: "febrile" | "respiratory" | "gastrointestinal";
  region: string;
  district: string | null;
  cases: number;
  expected: number;
  p_value: number;
  outbreak: boolean;
  prevalence: number;
  symptoms: Record<string, number>;
  localities: Record<string, number>;
  centre_lat: number;
  centre_lng: number;
  radius_km: number;
  first_onset: string;
  last_onset: string;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  advisory_id: string | null;
  yours: boolean;
  current: boolean;
  seen_at: string;
  reasons: string[];
  feedback: Verdict | null;
  feedback_note: string | null;
  feedback_at: string | null;
  feedback_by: string | null;
}

export type Verdict = "confirmed" | "false_alarm" | "unsure";

export interface Clusters {
  items: Cluster[];
  last_run_at: string | null;
  window_days: number;
  radius_km: number;
  min_people: number;
}

export const getClusters = (days: number, signal?: AbortSignal) => api.get<Clusters>("/clusters", { params: { days }, signal }).then((r) => r.data);
export const reviewCluster = (id: string, verdict: Verdict, note: string) =>
  api.post<Cluster>(`/clusters/${id}/feedback`, { verdict, note }).then((r) => r.data);
export const runClustering = () => api.post<Clusters>("/clusters/run").then((r) => r.data);
export const acknowledgeCluster = (id: string) => api.post<Cluster>(`/clusters/${id}/acknowledge`).then((r) => r.data);
