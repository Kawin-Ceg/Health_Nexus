import type { ThemeChoice } from "../lib/theme";
import { api } from "./api";

export type ConsentType = "community_surveillance" | "health_tracking" | "phc_worker_access" | "research_analytics";

export type FlagSeverity = "critical" | "high" | "moderate" | "low";

/** Everything is always shown in the app; these choose what is also emailed. */
export interface Preferences {
  theme: ThemeChoice;
  language: "en" | "ta" | "hi";
  notifications: { alerts: { email: boolean }; visits: { email: boolean } };
  alert_email_min_severity: FlagSeverity;
  working_hours: { start: string; end: string };
  reading_reminders: boolean;
}

export interface Concern {
  id: string;
  ticket_ref: string;
  category:
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
  description: string;
  status: "open" | "in_review" | "resolved" | "rejected";
  admin_note: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
}

export interface Centre {
  id: string;
  name: string;
  block: string | null;
  workers_assigned: number;
  is_current: boolean;
}

export interface HealthCentre {
  district: string | null;
  state: string | null;
  current: Centre | null;
  options: Centre[];
}

export interface About {
  app: string;
  version: string;
  role: string;
  facility: string | null;
  data_held: { readings: number; alerts: number; visits: number; concerns: number; consent_changes: number };
  who_can_see: string;
  scoring_note: string;
}

export interface Profile {
  id: string;
  name: string;
  email: string;
  pending_email: string | null;
  role: string;
  phone: string | null;
  bio: string | null;
  location: string | null;
  department: string | null;
  date_of_birth: string | null;
  avatar_url: string | null;
  cover_url: string | null;
  facility: string | null;
  designation: string | null;
  created_at: string;
}

type DeepPartial<T> = { [K in keyof T]?: T[K] extends object ? DeepPartial<T[K]> : T[K] };

const data = <T,>(p: Promise<{ data: T }>) => p.then((r) => r.data);

export const getPreferences = () => data(api.get<Preferences>("/settings/preferences"));
export const updatePreferences = (patch: DeepPartial<Preferences>) => data(api.patch<Preferences>("/settings/preferences", patch));

export const getConsents = () => data(api.get<{ consents: Record<ConsentType, boolean | null> }>("/settings/consents"));
export const updateConsent = (consent_type: ConsentType, granted: boolean) =>
  data(api.patch<{ consents: Record<ConsentType, boolean | null> }>("/settings/consents", { consents: [{ consent_type, granted }] }));
export const getConsentHistory = () =>
  data(api.get<{ id: string; consent_type: ConsentType; granted: boolean; source: string; created_at: string }[]>("/settings/consents/history"));

export const getAbout = () => data(api.get<About>("/settings/about"));

/** The export arrives as JSON; turned into a file the browser saves. */
export async function downloadExport(): Promise<void> {
  const response = await api.get<Blob>("/settings/export", { responseType: "blob" });
  const url = URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = `healthnexus-export-${new Date().toISOString().slice(0, 10)}.json`;
  link.click();
  URL.revokeObjectURL(url);
}

export const changePassword = (current_password: string, new_password: string) =>
  data(api.post<{ detail: string }>("/settings/password", { current_password, new_password }));
export const deactivate = (password: string) =>
  data(api.post<{ detail: string }>("/settings/deactivate", { password, confirm: "DEACTIVATE" }));

export const listConcerns = () => data(api.get<Concern[]>("/settings/concerns"));
export const raiseConcern = (category: Concern["category"], description: string, subjectId?: string) =>
  data(api.post<Concern>("/settings/concerns", { category, description, ...(subjectId ? { subject_id: subjectId } : {}) }));

export const getHealthCentre = () => data(api.get<HealthCentre>("/settings/health-centre"));
export const changeHealthCentre = (phc_id: string) => data(api.patch<HealthCentre>("/settings/health-centre", { phc_id }));

export const getProfile = () => data(api.get<Profile>("/profile"));
export const updateProfile = (patch: Partial<Pick<Profile, "name" | "phone" | "bio" | "location" | "department" | "date_of_birth">>) =>
  data(api.patch<Profile>("/profile", patch));
export function uploadImage(kind: "avatar" | "cover", file: File) {
  const form = new FormData();
  form.append("file", file);
  return data(api.post<Profile>(`/profile/${kind}`, form));
}
export const removeImage = (kind: "avatar" | "cover") => data(api.delete<Profile>(`/profile/${kind}`));
export const requestEmailChange = (new_email: string, password: string) =>
  data(api.post<{ detail: string }>("/profile/email", { new_email, password }));
export const confirmEmailChange = (token: string) => data(api.post<{ detail: string }>("/profile/email/confirm", { token }));
