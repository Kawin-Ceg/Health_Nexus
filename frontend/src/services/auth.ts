import { api, refreshSession, setAccessToken } from "./api";

export type Role = "user" | "pending_phc" | "phc_worker" | "admin";

export type Designation =
  | "medical_officer"
  | "staff_nurse"
  | "health_inspector"
  | "asha_supervisor"
  | "block_health_supervisor";

export interface Application {
  employee_id: string;
  designation: Designation;
  phc_name: string;
  district: string;
  state: string;
  years_of_service: number;
  status: "pending" | "approved" | "rejected";
  rejection_reason?: string | null;
  created_at: string;
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
  is_verified: boolean;
  profile_completed: boolean;
  consent: boolean;
  phc_id: string | null;
  state: string | null;
  district: string | null;
  created_at: string;
  /** Only for pending_phc accounts. */
  application?: Application | null;
}

export interface AuthPayload {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: User;
}

export interface SessionInfo {
  id: string;
  device_label: string | null;
  ip_address: string | null;
  created_at: string;
  last_activity_at: string;
  is_current: boolean;
}

export interface CitizenSignup {
  name: string;
  email: string;
  password: string;
}

export interface PhcWorkerSignup extends CitizenSignup {
  employee_id: string;
  designation: Designation;
  phc_name: string;
  district: string;
  state: string;
  years_of_service: number;
}

export const DESIGNATIONS: { value: Designation; label: string }[] = [
  { value: "medical_officer", label: "Medical Officer" },
  { value: "staff_nurse", label: "Staff Nurse" },
  { value: "health_inspector", label: "Health Inspector" },
  { value: "asha_supervisor", label: "ASHA Supervisor" },
  { value: "block_health_supervisor", label: "Block Health Supervisor" },
];

export const registerCitizen = (body: CitizenSignup) => api.post<User>("/auth/register/citizen", body).then((r) => r.data);

export const registerPhcWorker = (body: PhcWorkerSignup) =>
  api.post<User>("/auth/register/phc-worker", body).then((r) => r.data);

export async function login(email: string, password: string): Promise<AuthPayload> {
  const { data } = await api.post<AuthPayload>("/auth/login", { email, password });
  setAccessToken(data.access_token);
  return data;
}

/** Restores a session from the httpOnly cookie. Deduplicated; see refreshSession. */
export const restoreSession = refreshSession;

export async function logout(): Promise<void> {
  try {
    await api.post("/auth/logout");
  } finally {
    setAccessToken(null);
  }
}

export const fetchMe = () => api.get<User>("/auth/me").then((r) => r.data);

export const listSessions = () => api.get<SessionInfo[]>("/auth/sessions").then((r) => r.data);
export const revokeOtherSessions = () => api.post("/auth/sessions/revoke-others");
export const revokeSession = (id: string) => api.delete(`/auth/sessions/${id}`);

export const sendVerificationEmail = () => api.post<{ detail: string }>("/auth/email/send-verification").then((r) => r.data);
export const verifyEmail = (token: string) => api.post<{ detail: string }>("/auth/email/verify", { token }).then((r) => r.data);

export const forgotPassword = (email: string) => api.post<{ detail: string }>("/auth/password/forgot", { email }).then((r) => r.data);
export const resetPassword = (token: string, new_password: string) =>
  api.post<{ detail: string }>("/auth/password/reset", { token, new_password }).then((r) => r.data);
