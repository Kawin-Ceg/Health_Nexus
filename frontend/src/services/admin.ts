import { api } from "./api";
import type { VerificationDocument } from "./documents";
import type { Designation, Role } from "./auth";

export type ApplicationStatus = "pending" | "approved" | "rejected";
export type ConcernStatus = "open" | "in_review" | "resolved" | "rejected";
export type ConcernCategory =
  | "data_misuse"
  | "incorrect_diagnosis_flag"
  | "harassment"
  | "access_request"
  | "other"
  | "device_issue"
  | "app_problem"
  | "worker_conduct"
  | "worker_no_show"
  | "citizen_missed_visits"
  | "citizen_conduct";
export type ConcernStage = "not_reviewed" | "in_progress" | "action_taken";

export interface EvidenceVisit {
  when: string;
  at: string;
  location: string | null;
  reason: string | null;
  worker: string | null;
  status: string;
  explanation: string | null;
}

export interface Evidence {
  kind: "missed_visits" | "worker_no_show" | "device";
  window_days?: number;
  threshold?: number;
  missed?: number;
  unexplained?: number;
  eligible?: boolean;
  visits?: EvidenceVisit[];
  last_sync?: string | null;
  last_7_days?: Record<string, number>;
}
export type AccountStatus = "active" | "inactive" | "unverified";

export interface Overview {
  users_by_role: Record<Role, number>;
  inactive_accounts: number;
  unverified_accounts: number;
  pending_applications: number;
  workers_without_facility: number;
  open_concerns: number;
  readings_last_7_days: number;
  open_flags: number;
  facilities_active: number;
  assistant_questions_last_7_days: number;
  oldest_pending_at: string | null;
  area: string | null;
  pending_today: number;
  pending_over_3_days: number;
  flags_daily: number[];
  top_flag_centres: { name: string; count: number }[];
  oldest_applications: { id: string; name: string; centre: string; created_at: string }[];
  open_concern_list: { id: string; ref: string; category: string; subject: string; status: string; created_at: string }[];
  concerns_in_review: number;
  open_flags_high: number;
  centres_without_workers: number;
  citizen_activity: Record<string, number[]>;
  worker_activity: Record<string, number[]>;
}

export interface PeriodTotals {
  scheduled: number;
  done: number;
  missed: number;
  examinations: number;
  advisories: number;
  has_data: boolean;
}

export interface CentreActivity {
  facility_id: string;
  name: string;
  district: string;
  workers: number;
  citizens: number;
  citizens_monitored: number;
  flags_open: number;
  flags_critical: number;
  upcoming_visits: number;
  range_start: string;
  range_end: string;
  current: PeriodTotals;
  previous: PeriodTotals;
  weeks: { start: string; end: string; scheduled: number; done: number; missed: number }[];
}

export const getCentreActivity = (facilityId: string, days: number, signal?: AbortSignal) =>
  get<CentreActivity>("/admin/centre-activity", { facility_id: facilityId, days }, signal);

export interface FacilityOption {
  id: string;
  facility_code: string;
  name: string;
  district: string;
  state: string;
  block: string | null;
  is_active: boolean;
}

export interface ApplicationItem {
  id: string;
  applicant: { id: string; name: string; email: string; role: Role; is_verified: boolean; is_active: boolean; phc_id: string | null };
  employee_id: string;
  designation: Designation;
  phc_name: string;
  district: string;
  state: string;
  years_of_service: number;
  status: ApplicationStatus;
  rejection_reason: string | null;
  facility: FacilityOption | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string;
}

export interface ApplicationDetail extends ApplicationItem {
  suggested_facility: FacilityOption | null;
  history: { action: string; from_status: string | null; to_status: string; reason: string | null; actor: string | null; created_at: string }[];
  documents: VerificationDocument[];
}

export interface Account {
  id: string;
  name: string;
  email: string;
  role: Role;
  is_active: boolean;
  is_verified: boolean;
  profile_completed: boolean;
  facility: string | null;
  district: string | null;
  state: string | null;
  created_at: string;
  deactivated_at: string | null;
}

export interface ConcernItem {
  id: string;
  ticket_ref: string;
  category: ConcernCategory;
  description: string;
  status: ConcernStatus;
  admin_note: string | null;
  raised_by: string;
  raised_by_email: string;
  raised_by_role: Role;
  raised_by_district: string | null;
  subject: string | null;
  subject_role: Role | null;
  evidence: Evidence | null;
  handled_by: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
}

export interface AuditItem {
  source: "account" | "verification";
  action: string;
  actor: string | null;
  entity: string;
  entity_id: string | null;
  detail: string | null;
  ip_address: string;
  created_at: string;
}

const get = <T,>(url: string, params: object | undefined, signal?: AbortSignal) =>
  api.get<T>(url, { params, signal }).then((r) => r.data);
const post = <T,>(url: string, body: object = {}) => api.post<T>(url, body).then((r) => r.data);
const clean = (p: object) => Object.fromEntries(Object.entries(p).filter(([, v]) => v !== "" && v != null));

export const getOverview = (signal?: AbortSignal) => get<Overview>("/admin/overview", undefined, signal);

export const getApplications = (
  p: { status?: ApplicationStatus | ""; q?: string; district?: string; designation?: string; days?: number | "" },
  signal?: AbortSignal,
) =>
  get<{ items: ApplicationItem[]; total: number; counts: Record<ApplicationStatus, number>; districts: string[] }>(
    "/admin/applications",
    clean(p),
    signal,
  );
export const getApplication = (id: string, signal?: AbortSignal) => get<ApplicationDetail>(`/admin/applications/${id}`, undefined, signal);
export const approveApplication = (id: string, facility_id: string, note?: string) =>
  post<ApplicationDetail>(`/admin/applications/${id}/approve`, { facility_id, note: note || undefined });
export const rejectApplication = (id: string, reason: string) => post<ApplicationDetail>(`/admin/applications/${id}/reject`, { reason });
export const revokeApplication = (id: string, reason: string) => post<ApplicationDetail>(`/admin/applications/${id}/revoke`, { reason });

export const searchFacilities = (p: { q?: string; district?: string; state?: string }, signal?: AbortSignal) =>
  get<FacilityOption[]>("/admin/facilities", clean(p), signal);

export const getAccounts = (
  p: { role?: Role | ""; status?: AccountStatus | ""; q?: string; sort?: string; limit: number; offset: number },
  signal?: AbortSignal,
) => get<{ items: Account[]; total: number; limit: number; offset: number }>("/admin/users", clean(p), signal);
export const deactivateAccount = (id: string, reason: string) => post<Account>(`/admin/users/${id}/deactivate`, { reason });
export const reactivateAccount = (id: string) => post<Account>(`/admin/users/${id}/reactivate`);

export const getConcerns = (
  p: { status?: ConcernStatus | ""; category?: ConcernCategory | ""; raiser?: "user" | "phc_worker"; stage?: ConcernStage; q?: string; days?: number | "" },
  signal?: AbortSignal,
) => get<{ items: ConcernItem[]; total: number; counts: Record<ConcernStatus | ConcernStage, number> }>("/admin/concerns", clean(p), signal);
export const updateConcern = (id: string, body: { status: ConcernStatus; admin_note?: string }) =>
  api.patch<ConcernItem>(`/admin/concerns/${id}`, body).then((r) => r.data);

export const getAudit = (source: "" | "account" | "verification", signal?: AbortSignal) =>
  get<AuditItem[]>("/admin/audit", clean({ source }), signal);

/** De-identified readings of citizens who allowed research use, saved as a CSV file. */
export async function downloadResearchExport(days: number): Promise<void> {
  const response = await api.get<Blob>("/admin/research-export", { params: { days }, responseType: "blob" });
  const url = URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = `healthnexus-research-${new Date().toISOString().slice(0, 10)}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

export interface CentreInput {
  facility_code: string;
  name: string;
  district: string;
  state: string;
  block: string | null;
  official_email_domain: string | null;
  latitude: number | null;
  longitude: number | null;
}

export interface Centre extends CentreInput {
  id: string;
  is_active: boolean;
  is_placeholder: boolean;
  workers: number;
  citizens: number;
}

export const getCentres = (
  p: { q?: string; district?: string; state?: "all" | "active" | "inactive"; limit?: number; offset?: number },
  signal?: AbortSignal,
) => get<{ items: Centre[]; total: number; districts: string[] }>("/admin/registry", clean(p), signal);
export const createCentre = (input: CentreInput) => post<Centre>("/admin/registry", input);
export const editCentre = (id: string, input: Partial<CentreInput>) =>
  api.patch<Centre>(`/admin/registry/${id}`, input).then((r) => r.data);
export const setCentreActive = (id: string, active: boolean) =>
  post<Centre>(`/admin/registry/${id}/${active ? "reactivate" : "deactivate"}`);
