import type { Severity } from "../lib/severity";
import type { Advisory } from "./advisories";
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
  vitals: Record<string, number>;
  source: ReadingSource;
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
  watch: string[];
  population: PopulationCheck | null;
}

export interface PopulationCheck {
  score: number;
  percentile: number;
  features: string[];
  version: string;
  unusual: boolean;
  note: string;
}

export type BaselineStage = "learning" | "blending" | "personal";

export interface VitalCheck {
  key: string;
  value: number;
  stage: BaselineStage;
  readings: number;
  weight: number;
  published: number;
  safety: boolean;
  baseline: number | null;
  spread: number | null;
  z: number | null;
  personal: number | null;
  confirmed: boolean;
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
  population: PopulationCheck | null;
  source: ReadingSource;
  watch_slot: WatchSlotKey | null;
  recorded_by: string | null;
  location: string | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
}

export type ReadingSource = "watch" | "phc" | "self";

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

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

export type VisitType = "home" | "centre" | "follow_up" | "vaccination" | "maternal" | "screening";

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
  missed_reason?: string | null;
  visit_type?: VisitType;
  duration_minutes?: number;
  notes?: string | null;
  cancelled_by?: "citizen" | "worker" | null;
  cancel_reason?: string | null;
  worker_phone?: string | null;
  booked_at?: string | null;
  cancelled_at?: string | null;
  missed_reason_at?: string | null;
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
  state?: "normal" | "awaiting" | "reviewed" | null;
  reviewer?: string | null;
  q?: string | null;
}

let metricsCache: Promise<MetricsInfo> | null = null;

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

export type WatchSlotKey = "morning" | "afternoon" | "evening" | "night";

export interface WatchState {
  connected: boolean;
  brand: string | null;
  current_slot: WatchSlotKey;
  day: string;
  slots: { key: WatchSlotKey; label: string; hours: string; reading_id: string | null; measured_at: string | null; vitals: Record<string, number> | null }[];
}

export const getWatch = (signal?: AbortSignal) => api.get<WatchState>("/health/watch", { signal }).then((r) => r.data);
export const connectWatch = (brand: string) => api.post<WatchState>("/health/watch/connect", { brand }).then((r) => r.data);
export const disconnectWatch = () => api.post<WatchState>("/health/watch/disconnect").then((r) => r.data);
export const syncWatch = () =>
  api.post<{ reading: VitalsResult; slot: WatchSlotKey; already_synced: boolean }>("/health/watch/sync").then((r) => r.data);

export const getHistory = (q: HistoryQuery, signal?: AbortSignal) =>
  api
    .get<Page<Reading> & { reviewers: { id: string; name: string }[] }>("/health/history", {
      params: {
        page: q.page,
        page_size: q.page_size,
        metric: q.metric || undefined,
        days: q.days || undefined,
        flagged_only: q.flagged_only || undefined,
        state: q.state || undefined,
        reviewer: q.reviewer || undefined,
        q: q.q || undefined,
      },
      signal,
    })
    .then((r) => r.data);

export const getSummary = (signal?: AbortSignal) => api.get<Summary>("/health/summary", { signal }).then((r) => r.data);

export const getBaselineStatus = (signal?: AbortSignal) =>
  api.get<BaselineStatus>("/health/baseline", { signal }).then((r) => r.data);

export const deleteReading = (id: string) => api.delete(`/health/readings/${id}`);

export const getAlerts = (signal?: AbortSignal) =>
  api.get<{ alerts: AlertItem[]; advisories: Advisory[]; unread: number }>("/alerts", { signal }).then((r) => r.data);

export const getUnreadCount = (signal?: AbortSignal) =>
  api.get<{ unread: number }>("/alerts/unread-count", { signal }).then((r) => r.data.unread);

export const markRead = (ids?: string[]) => api.post<{ updated: number }>("/alerts/mark-read", ids ? { ids } : {}).then((r) => r.data);

export const getMySchedule = (signal?: AbortSignal) =>
  api.get<{ visits: Visit[] }>("/schedule/mine", { signal }).then((r) => r.data.visits);
export const cancelMyVisit = (id: string, reason: string) => api.post<Visit>(`/schedule/mine/${id}/cancel`, { reason }).then((r) => r.data);
export const explainMissedVisit = (id: string, reason: string) => api.post<Visit>(`/schedule/mine/${id}/reason`, { reason }).then((r) => r.data);
