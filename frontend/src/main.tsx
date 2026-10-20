import { StrictMode, Suspense, lazy, type ComponentType } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/app/AppShell";
import { ToastProvider } from "./components/app/Toaster";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { RedirectIfAuthenticated } from "./components/RedirectIfAuthenticated";
import { AuthProvider } from "./context/AuthContext";
import { paths } from "./lib/routes";
import { initTheme } from "./lib/theme";
/* Every page is loaded on demand. Without this the landing page pulls the whole
   app down with it, Recharts and Leaflet included, before anyone signs in. */
const page = <T extends string>(loader: () => Promise<Record<string, unknown>>, name: T) =>
  lazy(() => loader().then((m) => ({ default: m[name] as ComponentType })));

const Assistant = page(() => import("./pages/Assistant"), "Assistant");
const ConfirmEmail = page(() => import("./pages/ConfirmEmail"), "ConfirmEmail");
const Notifications = page(() => import("./pages/Notifications"), "Notifications");
const Advisories = page(() => import("./pages/Advisories"), "Advisories");
const Outbreaks = page(() => import("./pages/Outbreaks"), "Outbreaks");
const Profile = page(() => import("./pages/Profile"), "Profile");
const Settings = page(() => import("./pages/Settings"), "Settings");
const CitizenAlerts = page(() => import("./pages/citizen/Alerts"), "CitizenAlerts");
const CitizenVisits = page(() => import("./pages/citizen/Visits"), "CitizenVisits");
const CitizenDashboard = page(() => import("./pages/citizen/Dashboard"), "CitizenDashboard");
const History = page(() => import("./pages/citizen/History"), "History");
const Watch = page(() => import("./pages/citizen/Watch"), "Watch");
const RecordExam = page(() => import("./pages/phc/RecordExam"), "RecordExam");
const CitizenRecord = page(() => import("./pages/phc/CitizenRecord"), "CitizenRecord");
const Citizens = page(() => import("./pages/phc/Citizens"), "Citizens");
const PhcAlerts = page(() => import("./pages/phc/PhcAlerts"), "PhcAlerts");
const PhcDashboard = page(() => import("./pages/phc/PhcDashboard"), "PhcDashboard");
const Reports = page(() => import("./pages/phc/Reports"), "Reports");
const RiskMap = page(() => import("./pages/phc/RiskMap"), "RiskMap");
const Schedule = page(() => import("./pages/phc/Schedule"), "Schedule");
const AdminDashboard = page(() => import("./pages/admin/AdminDashboard"), "AdminDashboard");
const Applications = page(() => import("./pages/admin/Applications"), "Applications");
const Accounts = page(() => import("./pages/admin/Accounts"), "Accounts");
const Concerns = page(() => import("./pages/admin/Concerns"), "Concerns");
const AuditLog = page(() => import("./pages/admin/AuditLog"), "AuditLog");
const Centres = page(() => import("./pages/admin/Centres"), "Centres");
const PrivacyPolicy = page(() => import("./pages/legal/PrivacyPolicy"), "PrivacyPolicy");
const Terms = page(() => import("./pages/legal/Terms"), "Terms");
const ForgotPassword = page(() => import("./pages/ForgotPassword"), "ForgotPassword");
const LandingPage = page(() => import("./pages/LandingPage"), "LandingPage");
const LoginPage = page(() => import("./pages/LoginPage"), "LoginPage");
const Onboarding = page(() => import("./pages/Onboarding"), "Onboarding");
const PendingApproval = page(() => import("./pages/PendingApproval"), "PendingApproval");
const PHCSignup = page(() => import("./pages/PHCSignup"), "PHCSignup");
const ResetPassword = page(() => import("./pages/ResetPassword"), "ResetPassword");
const SignupPage = page(() => import("./pages/SignupPage"), "SignupPage");
const VerifyEmail = page(() => import("./pages/VerifyEmail"), "VerifyEmail");
const SessionsPage = page(() => import("./pages/account/SessionsPage"), "SessionsPage");
const NotFound = page(() => import("./pages/errors/NotFound"), "NotFound");
const Unauthorized = page(() => import("./pages/errors/Unauthorized"), "Unauthorized");

import "./styles/global.css";

// Follow the system theme until the signed-in user's saved preference loads (AppShell).
initTheme();

/** Shown while a route chunk loads. Deliberately quiet: on a fast connection it
 *  flashes for a few frames, and a spinner there reads as an error. */
function RouteFallback() {
  return <div role="status" aria-live="polite" className="sr-only">Loading</div>;
}

const root = document.getElementById("root");
if (!root) throw new Error("#root element missing from index.html");

createRoot(root).render(
  <StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <ToastProvider>
          <Suspense fallback={<RouteFallback />}>
          <Routes>
            {/* Signed-out visitors only */}
            <Route element={<RedirectIfAuthenticated />}>
              <Route path={paths.home} element={<LandingPage />} />
              <Route path={paths.login} element={<LoginPage />} />
              <Route path={paths.signup} element={<SignupPage />} />
              <Route path={paths.phcSignup} element={<PHCSignup />} />
            </Route>

            {/* Public: these links are opened on devices that have no session */}
            <Route path={paths.verifyEmail} element={<VerifyEmail />} />
            <Route path={paths.forgotPassword} element={<ForgotPassword />} />
            <Route path={paths.resetPassword} element={<ResetPassword />} />
            <Route path={paths.privacy} element={<PrivacyPolicy />} />
            <Route path={paths.terms} element={<Terms />} />

            {/* Every signed-in role */}
            <Route element={<ProtectedRoute allowedRoles={["user", "pending_phc", "phc_worker", "admin"]} allowUnverified />}>
              <Route path={paths.sessions} element={<SessionsPage />} />
            </Route>

            <Route element={<ProtectedRoute allowedRoles={["pending_phc"]} />}>
              <Route path={paths.pendingApproval} element={<PendingApproval />} />
            </Route>

            <Route element={<ProtectedRoute allowedRoles={["user"]} allowIncompleteProfile />}>
              <Route path={paths.onboarding} element={<Onboarding />} />
            </Route>

            <Route path={paths.confirmEmail} element={<ConfirmEmail />} />

            <Route element={<ProtectedRoute allowedRoles={["user"]} />}>
              <Route element={<AppShell />}>
                <Route path={paths.citizenHome} element={<CitizenDashboard />} />
                <Route path={paths.watch} element={<Watch />} />
                <Route path={paths.history} element={<History />} />
                <Route path={paths.citizenAlerts} element={<CitizenAlerts />} />
                <Route path={paths.citizenVisits} element={<CitizenVisits />} />
              </Route>
            </Route>
            <Route element={<ProtectedRoute allowedRoles={["phc_worker"]} />}>
              <Route element={<AppShell />}>
                <Route path={paths.phcHome} element={<PhcDashboard />} />
                <Route path={paths.phcAlerts} element={<PhcAlerts />} />
                <Route path={paths.phcCitizens} element={<Citizens />} />
                <Route path="/phc/citizens/:userId/exam" element={<RecordExam />} />
                <Route path="/phc/citizens/:userId" element={<CitizenRecord />} />
                <Route path={paths.phcSchedule} element={<Schedule />} />
                <Route path={paths.phcReports} element={<Reports />} />
                <Route path={paths.phcMap} element={<RiskMap />} />
                <Route path={paths.notifications} element={<Notifications />} />
              </Route>
            </Route>
            <Route element={<ProtectedRoute allowedRoles={["user", "phc_worker"]} />}>
              <Route element={<AppShell />}>
                <Route path={paths.settings} element={<Settings />} />
                <Route path={paths.profile} element={<Profile />} />
              </Route>
            </Route>
            <Route element={<ProtectedRoute allowedRoles={["user", "phc_worker", "admin"]} />}>
              <Route element={<AppShell />}>
                <Route path={paths.assistant} element={<Assistant />} />
              </Route>
            </Route>
            <Route element={<ProtectedRoute allowedRoles={["phc_worker", "admin"]} />}>
              <Route element={<AppShell />}>
                <Route path={paths.advisories} element={<Advisories />} />
                <Route path={paths.outbreaks} element={<Outbreaks />} />
              </Route>
            </Route>
            <Route element={<ProtectedRoute allowedRoles={["admin"]} />}>
              <Route element={<AppShell />}>
                <Route path={paths.adminHome} element={<AdminDashboard />} />
                <Route path={paths.adminApplications} element={<Applications />} />
                <Route path={paths.adminCentres} element={<Centres />} />
                <Route path={paths.adminAccounts} element={<Accounts />} />
                <Route path={paths.adminConcerns} element={<Concerns />} />
                <Route path={paths.adminAudit} element={<AuditLog />} />
              </Route>
            </Route>

            <Route path={paths.unauthorized} element={<Unauthorized />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
          </Suspense>
          </ToastProvider>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  </StrictMode>,
);
