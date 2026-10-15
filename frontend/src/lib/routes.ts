import type { User } from "../services/auth";

export const paths = {
  home: "/",
  login: "/login",
  signup: "/signup",
  phcSignup: "/signup/phc-worker",
  verifyEmail: "/verify-email",
  forgotPassword: "/forgot-password",
  resetPassword: "/reset-password",
  pendingApproval: "/pending-approval",
  onboarding: "/onboarding",
  citizenHome: "/app",
  submitVitals: "/app/log",
  history: "/app/history",
  citizenAlerts: "/app/alerts",
  phcHome: "/phc",
  phcAlerts: "/phc/alerts",
  phcCitizens: "/phc/citizens",
  phcSchedule: "/phc/schedule",
  phcReports: "/phc/reports",
  phcMap: "/phc/map",
  notifications: "/notifications",
  advisories: "/advisories",
  outbreaks: "/outbreaks",
  settings: "/settings",
  profile: "/profile",
  confirmEmail: "/confirm-email",
  adminHome: "/admin",
  adminApplications: "/admin/applications",
  adminAccounts: "/admin/accounts",
  adminConcerns: "/admin/concerns",
  adminAudit: "/admin/audit",
  adminCentres: "/admin/centres",
  assistant: "/assistant",
  sessions: "/account/sessions",
  unauthorized: "/unauthorized",
  privacy: "/privacy-policy",
  terms: "/terms",
} as const;

export const citizenRecordPath = (userId: string) => `/phc/citizens/${userId}`;

/**
 * Where a signed-in user belongs, decided by their state. The one place this is
 * written down: login, the redirect guards and the "Continue" buttons all use it.
 */
export function destinationFor(user: User): string {
  if (!user.is_verified) return paths.verifyEmail;
  switch (user.role) {
    case "pending_phc":
      return paths.pendingApproval;
    case "phc_worker":
      return paths.phcHome;
    case "admin":
      return paths.adminHome;
    case "user":
      return user.profile_completed ? paths.citizenHome : paths.onboarding;
  }
}
