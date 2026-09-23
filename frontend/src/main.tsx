import { StrictMode } from "react";
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
import { ConfirmEmail } from "./pages/ConfirmEmail";
import { Notifications } from "./pages/Notifications";
import { Profile } from "./pages/Profile";
import { Settings } from "./pages/Settings";
import { CitizenAlerts } from "./pages/citizen/Alerts";
import { CitizenDashboard } from "./pages/citizen/Dashboard";
import { History } from "./pages/citizen/History";
import { SubmitVitals } from "./pages/citizen/SubmitVitals";
import { CitizenRecord } from "./pages/phc/CitizenRecord";
import { Citizens } from "./pages/phc/Citizens";
import { PhcAlerts } from "./pages/phc/PhcAlerts";
import { PhcDashboard } from "./pages/phc/PhcDashboard";
import { Reports } from "./pages/phc/Reports";
import { RiskMap } from "./pages/phc/RiskMap";
import { Schedule } from "./pages/phc/Schedule";
import { ForgotPassword } from "./pages/ForgotPassword";
import { LandingPage } from "./pages/LandingPage";
import { LoginPage } from "./pages/LoginPage";
import { Onboarding } from "./pages/Onboarding";
import { PendingApproval } from "./pages/PendingApproval";
import { PHCSignup } from "./pages/PHCSignup";
import { ResetPassword } from "./pages/ResetPassword";
import { SignupPage } from "./pages/SignupPage";
import { VerifyEmail } from "./pages/VerifyEmail";
import { SessionsPage } from "./pages/account/SessionsPage";
import { NotFound } from "./pages/errors/NotFound";
import { Unauthorized } from "./pages/errors/Unauthorized";
import "./styles/global.css";

// Follow the system theme until the signed-in user's saved preference loads (AppShell).
initTheme();

const root = document.getElementById("root");
if (!root) throw new Error("#root element missing from index.html");

createRoot(root).render(
  <StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
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
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  </StrictMode>,
);
