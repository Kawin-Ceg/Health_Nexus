import type { Severity } from "../lib/severity";
import { api } from "./api";
import type { AlertItem, Baseline, PopulationCheck, Visit, VisitPerson, VitalCheck } from "./health";

export type Engagement = "attention" | "never_logged" | "silent" | "ok";
export type Resolution = "reviewed" | "dismissed";
export type DismissReason = "false_positive" | "already_treated" | "contacted" | "other";

export interface Facility {
  id: string;
  name: string;
  district: string;
  block: string | null;
}

export interface Dashboard {
  facility: Facility;
  citizens: number;
  citizens_flagged: number;
  open_flags: number;
  open_by_severity: Record<Severity, number>;
  readings_last_7_days: number;
  citizens_submitting_last_7_days: number;
  engagement: Record<Engagement, number>;
  silent_after_days: number;
  visits_needing_outcome: number;
  visits_today: number;
}

export interface Kpi {
  key: string;
  label: string;
  weeks: { week_start: string; value: number; partial: boolean }[];
}

export interface Case {
  processed_id: string;
  citizen: VisitPerson;
  severity: Severity;
  anomaly_score: number;
  signal: string | null;
  features: Record<string, number>;
  vitals: Record<string, number>;
  symptoms: string[];
  measured_at: string;
  basis: string | null;
  population: PopulationCheck | null;
}

export interface WorkItem {
  citizen: VisitPerson;
  open_flags: number;
  worst_severity: Severity;
  worst_signal: string | null;
  first_flagged_at: string;
  last_flagged_at: string;
  flags: { processed_id: string; severity: Severity; signal: string | null; symptoms: string[]; measured_at: string; basis: string | null }[];
  flags_shown: number;
  next_visit: Visit | null;
}

export interface DirectoryItem {
  citizen: VisitPerson;
  age: number | null;
  gender: string | null;
  status: Engagement;
  open_flags: number;
  worst_severity: Severity | null;
  readings: number;
  last_reading_at: string | null;
  joined_at: string;
}

export interface Directory {
  items: DirectoryItem[];
  total: number;
  limit: number;
  offset: number;
  counts: Record<Engagement, number>;
  catchment_total: number;
  localities: { locality: string; citizens: number }[];
  silent_after_days: number;
}

export interface CitizenRecord {
  identity: {
    id: string;
    ref: string;
    name: string;
    phone: string | null;
    email: string;
    area: string | null;
    pincode: string | null;
    age: number | null;
    gender: string | null;
    blood_group: string | null;
    existing_conditions: string[];
    current_medications: string[];
    emergency_contact_name: string | null;
    emergency_contact_phone: string | null;
    joined_at: string;
  };
  window: { start: string; end: string; days: number };
  counts: { readings: number; flags: number; open_flags: number; alerts: number; visits: number };
  vitals: {
    key: string;
    latest: number;
    latest_at: string;
    position: "below" | "normal" | "above";
    readings: number;
    baseline: Baseline | null;
    z_score: number | null;
  }[];
  timeline: {
    reading_id: string;
    processed_id: string | null;
    measured_at: string;
    vitals: Record<string, number>;
    symptoms: string[];
    flagged: boolean;
    severity: Severity | null;
    signal: string | null;
    resolution: Resolution | null;
    reviewed_at: string | null;
    basis: string | null;
    /** Empty for readings scored before the model stored its working. */
    checks: VitalCheck[];
    population: PopulationCheck | null;
  }[];
  timeline_truncated: boolean;
  timeline_limit: number;
  alerts: AlertItem[];
  visits: Visit[];
  upcoming_visits: Visit[];
  unresolved_before_window: { open_flags: number; oldest_flag_at: string | null; visits_without_outcome: number };
  min_baseline_readings: number;
}

export interface Reports {
  window: { start: string; end: string; days: number };
  readings: number;
  citizens_submitting: number;
  flags: number;
  flag_rate: number | null;
  catchment_now: number;
  daily: { date: string; readings: number; flags: number }[];
  localities: { locality: string; citizens: number; submitting: number; readings: number; flags: number }[];
  min_cell: number;
}

export interface LocalityRisk {
  locality: string;
  citizens: number;
  flagged: number;
  share: number;
  level: "high" | "elevated" | "some" | "none";
  lat: number | null;
  lng: number | null;
}

export interface RiskMap {
  facility: Facility;
  facility_lat: number | null;
  facility_lng: number | null;
  items: LocalityRisk[];
  min_cell: number;
}

export interface Schedule {
  counts: { needs_outcome: number; happening_now: number; today: number; upcoming: number; recent_outcomes: number };
  needs_outcome: Visit[];
  happening_now: Visit[];
  today: Visit[];
  upcoming: Visit[];
  recent_outcomes: Visit[];
  recent_window_days: number;
}

export interface ResolveBody {
  resolution?: Resolution;
  dismiss_reason?: DismissReason;
  note?: string;
}

const get = <T,>(url: string, params: object | undefined, signal?: AbortSignal) =>
  api.get<T>(url, { params, signal }).then((r) => r.data);

export const getDashboard = (signal?: AbortSignal) => get<Dashboard>("/phc/dashboard", undefined, signal);
export const getOverview = (signal?: AbortSignal) => get<{ kpis: Kpi[] }>("/phc/overview", undefined, signal);
export const getQueue = (p: { severity?: Severity | null; locality?: string; q?: string; limit?: number }, signal?: AbortSignal) =>
  get<{ items: Case[]; total: number }>("/phc/queue", { ...p, severity: p.severity || undefined, locality: p.locality || undefined, q: p.q || undefined }, signal);
export const markSeen = (processedId: string, body?: ResolveBody) =>
  api.post<{ cleared: number }>(`/phc/queue/${processedId}/seen`, body ?? {}).then((r) => r.data);
export const getWorklist = (p: { locality?: string; q?: string }, signal?: AbortSignal) =>
  get<{ items: WorkItem[]; total_citizens: number; limit: number }>("/phc/worklist", { locality: p.locality || undefined, q: p.q || undefined }, signal);
export const resolveCitizen = (userId: string, body?: ResolveBody) =>
  api.post<{ cleared: number }>(`/phc/worklist/citizens/${userId}/resolve`, body ?? {}).then((r) => r.data);
export const getDirectory = (
  p: { q?: string; locality?: string; status?: Engagement | null; limit: number; offset: number },
  signal?: AbortSignal,
) => get<Directory>("/phc/citizens", { ...p, q: p.q || undefined, locality: p.locality || undefined, status: p.status || undefined }, signal);
export const getRecord = (userId: string, days: number, signal?: AbortSignal) =>
  get<CitizenRecord>(`/phc/citizens/${userId}/record`, { days }, signal);
export const getReports = (days: number, signal?: AbortSignal) => get<Reports>("/phc/reports", { days }, signal);
export const getMap = (signal?: AbortSignal) => get<RiskMap>("/phc/map", undefined, signal);
export const getPhcBadge = (signal?: AbortSignal) =>
  get<{ unread: number; citizens_flagged: number }>("/phc-alerts/unread-count", undefined, signal);

export const bookVisit = (body: { citizen_id: string; case_id?: string | null; scheduled_for: string; reason?: string; location?: string }) =>
  api.post<Visit>("/phc/visits", body).then((r) => r.data);
export const getSchedule = (signal?: AbortSignal) => get<Schedule>("/schedule", undefined, signal);
export const updateVisit = (id: string, body: { action: "complete" | "cancel" | "miss" | "move"; scheduled_for?: string }) =>
  api.patch<Visit>(`/schedule/${id}`, body).then((r) => r.data);

export interface FeedItem {
  processed_id: string;
  citizen: VisitPerson;
  severity: Severity;
  signal: string | null;
  measured_at: string;
  status: "open" | "reviewed" | "dismissed";
  reviewed_by: string | null;
  reviewed_at: string | null;
}

export const getFeed = (signal?: AbortSignal) => get<{ items: FeedItem[]; days: number; limit: number }>("/phc/alerts", undefined, signal);
