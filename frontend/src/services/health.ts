import type { Severity } from "../lib/severity";
import { api } from "./api";

export interface Metric {
  key: string;
  label: string;
  unit: string;
  group: "blood_pressure" | "vitals" | "other";
  normal: [number, number] | null;
  plausible: [number, number];
  decimals: number;
}

export interface MetricsInfo {
  metrics: Metric[];
  common_symptoms: string[];
  min_baseline_readings: number;
}

export interface VitalsResult {
  id: string;
  measured_at: string;
  flagged: boolean;
  anomaly_score: number;
  severity: Severity | null;
  driver: string | null;
  signal: string | null;
  features: Record<string, number>;
  basis: string;
  earlier_readings: number;
  basis_note: string;
  reviewed_by_someone: boolean;
  model_version: string;
  checks: VitalCheck[];
  /** Unusual for this person, but waiting for a second reading before it flags. */
  watch: string[];
}

export type BaselineStage = "learning" | "blending" | "personal";

/** How one vital of a reading was judged by the anomaly model (backend services/scoring.py). */
export interface VitalCheck {
  key: string;
  value: number;
  stage: BaselineStage;
  /** Earlier readings of this vital the baseline could use. */
  readings: number;
  /** 0 = published normal range only, 1 = this person's baseline only. */
  weight: number;
  /** How far outside the published normal range, in half-band widths (0 inside). */
  published: number;
  /** Past a safety limit: counts whatever the person's usual is. */
  safety: boolean;
  baseline: number | null;
  spread: number | null;
  z: number | null;
  personal: number | null;
  confirmed: boolean;
  /** What it added to the score. Above 0 means it counted toward the flag. */
  contribution: number;
}

export interface VitalBaseline {
  key: string;
  readings: number;
  stage: BaselineStage;
  weight: number;
  baseline: number | null;
  spread: number | null;
  readings_to_start: number;
  readings_to_full: number;
}

export interface BaselineStatus {
  model_version: string;
  min_readings: number;
  full_readings: number;
  window: number;
  vitals: VitalBaseline[];
}

export interface Reading {
  id: string;
  measured_at: string;
  vitals: Record<string, number>;
  symptoms: string[];
  flagged: boolean;
  severity: Severity | null;
  signal: string | null;
  reviewed: boolean;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

/** The model's personal baseline: the median and robust spread of the last n readings. */
export interface Baseline {
  usual: number;
  spread: number;
  n: number;
}

export interface AlertItem {
  id: string;
  alert_type: "personal" | "community";
  severity: "low" | "medium" | "high";
  message: string;
  is_read: boolean;
  created_at: string;
}

export type VisitState = "upcoming" | "today" | "due_now" | "overdue" | "completed" | "cancelled" | "missed";

export interface VisitPerson {
  id: string;
  ref: string;
  name: string;
  phone: string | null;
  area: string | null;
}

export interface Visit {
  id: string;
  scheduled_for: string;
  reason: string | null;
  location: string | null;
  status: "scheduled" | "completed" | "cancelled" | "missed";
  state: VisitState;
  case_id: string | null;
  citizen: VisitPerson | null;
  worker_name: string | null;
}

export interface Summary {
  readings_total: number;
  readings_last_7_days: number;
  open_flags: number;
  unread_alerts: number;
  readings_until_baseline: number;
  baseline_window_days: number;
  latest: { key: string; value: number; measured_at: string; position: "below" | "normal" | "above"; baseline: Baseline | null }[];
  trend: { measured_at: string; vitals: Record<string, number>; flagged: boolean }[];
  trend_window_days: number;
  alerts: AlertItem[];
  next_visit: Visit | null;
  facility: { id: string; name: string; district: string; workers_assigned: number } | null;
}

export interface HistoryQuery {
  page: number;
  page_size: number;
  metric?: string | null;
  days?: number | null;
  flagged_only?: boolean;
}

let metricsCache: Promise<MetricsInfo> | null = null;

/** The vitals vocabulary never changes during a session: fetch it once. */
export function getMetrics(): Promise<MetricsInfo> {
  metricsCache ??= api
    .get<MetricsInfo>("/health/metrics")
    .then((r) => r.data)
    .catch((e) => {
      metricsCache = null;
      throw e;
    });
  return metricsCache;
}

export const submitVitals = (body: { vitals: Record<string, number>; symptoms: string[]; measured_at?: string }) =>
  api.post<VitalsResult>("/health/vitals", body).then((r) => r.data);

export const getHistory = (q: HistoryQuery, signal?: AbortSignal) =>
  api
    .get<Page<Reading>>("/health/history", {
      params: { page: q.page, page_size: q.page_size, metric: q.metric || undefined, days: q.days || undefined, flagged_only: q.flagged_only || undefined },
      signal,
    })
    .then((r) => r.data);

export const getSummary = (signal?: AbortSignal) => api.get<Summary>("/health/summary", { signal }).then((r) => r.data);

export const getBaselineStatus = (signal?: AbortSignal) =>
  api.get<BaselineStatus>("/health/baseline", { signal }).then((r) => r.data);

export const deleteReading = (id: string) => api.delete(`/health/readings/${id}`);

export const getAlerts = (signal?: AbortSignal) =>
  api.get<{ alerts: AlertItem[]; advisories: AlertItem[]; unread: number }>("/alerts", { signal }).then((r) => r.data);

export const getUnreadCount = (signal?: AbortSignal) =>
  api.get<{ unread: number }>("/alerts/unread-count", { signal }).then((r) => r.data.unread);

export const markRead = (ids?: string[]) => api.post<{ updated: number }>("/alerts/mark-read", ids ? { ids } : {}).then((r) => r.data);

export const getMySchedule = (signal?: AbortSignal) =>
  api.get<{ visits: Visit[] }>("/schedule/mine", { signal }).then((r) => r.data.visits);
