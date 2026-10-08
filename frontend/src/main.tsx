import { StrictMode, Suspense, lazy, type ComponentType } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { ComingSoon } from "./components/ComingSoon";
import { AppShell } from "./components/app/AppShell";
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

const ConfirmEmail = page(() => import("./pages/ConfirmEmail"), "ConfirmEmail");
const Notifications = page(() => import("./pages/Notifications"), "Notifications");
const Profile = page(() => import("./pages/Profile"), "Profile");
const Settings = page(() => import("./pages/Settings"), "Settings");
const CitizenAlerts = page(() => import("./pages/citizen/Alerts"), "CitizenAlerts");
const CitizenDashboard = page(() => import("./pages/citizen/Dashboard"), "CitizenDashboard");
const History = page(() => import("./pages/citizen/History"), "History");
const SubmitVitals = page(() => import("./pages/citizen/SubmitVitals"), "SubmitVitals");
const CitizenRecord = page(() => import("./pages/phc/CitizenRecord"), "CitizenRecord");
const Citizens = page(() => import("./pages/phc/Citizens"), "Citizens");
const PhcAlerts = page(() => import("./pages/phc/PhcAlerts"), "PhcAlerts");
const PhcDashboard = page(() => import("./pages/phc/PhcDashboard"), "PhcDashboard");
const Reports = page(() => import("./pages/phc/Reports"), "Reports");
const RiskMap = page(() => import("./pages/phc/RiskMap"), "RiskMap");
const Schedule = page(() => import("./pages/phc/Schedule"), "Schedule");
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
                <Route path={paths.submitVitals} element={<SubmitVitals />} />
                <Route path={paths.history} element={<History />} />
                <Route path={paths.citizenAlerts} element={<CitizenAlerts />} />
              </Route>
            </Route>
            <Route element={<ProtectedRoute allowedRoles={["phc_worker"]} />}>
              <Route element={<AppShell />}>
                <Route path={paths.phcHome} element={<PhcDashboard />} />
                <Route path={paths.phcAlerts} element={<PhcAlerts />} />
                <Route path={paths.phcCitizens} element={<Citizens />} />
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
            <Route element={<ProtectedRoute allowedRoles={["admin"]} />}>
              <Route path={paths.adminHome} element={<ComingSoon title="Admin console" />} />
            </Route>

            <Route path={paths.unauthorized} element={<Unauthorized />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
          </Suspense>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  </StrictMode>,
);
