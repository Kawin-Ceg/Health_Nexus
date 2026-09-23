import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { ComingSoon } from "./components/ComingSoon";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { RedirectIfAuthenticated } from "./components/RedirectIfAuthenticated";
import { AuthProvider } from "./context/AuthContext";
import { paths } from "./lib/routes";
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

// Follow the system theme: themes.css swaps the tokens under `.dark`.
const darkQuery = window.matchMedia("(prefers-color-scheme: dark)");
const applyTheme = () => document.documentElement.classList.toggle("dark", darkQuery.matches);
applyTheme();
darkQuery.addEventListener("change", applyTheme);

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

            {/* Placeholders for later modules */}
            <Route element={<ProtectedRoute allowedRoles={["user"]} />}>
              <Route path={paths.citizenHome} element={<ComingSoon title="Citizen dashboard" />} />
            </Route>
            <Route element={<ProtectedRoute allowedRoles={["phc_worker"]} />}>
              <Route path={paths.phcHome} element={<ComingSoon title="PHC worker dashboard" />} />
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
