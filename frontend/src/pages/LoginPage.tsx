import { Link, useLocation } from "react-router-dom";
import { AuthLayout } from "../components/auth/AuthLayout";
import { Banner } from "../components/auth/Banner";
import { LoginForm } from "../components/auth/LoginForm";
import { useAuth } from "../context/AuthContext";
import { paths } from "../lib/routes";

const REASONS = {
  inactivity: "You were signed out after 48 hours of inactivity. Sign in again to continue.",
  expired: "Your session has ended. Sign in again to continue.",
};

export function LoginPage() {
  const { sessionEndReason } = useAuth();
  const notice = (useLocation().state as { notice?: string } | null)?.notice;

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Sign in to continue."
      footer={
        <>
          <Link to={paths.signup}>Create an account</Link>
          <Link to={paths.phcSignup}>Apply as a PHC worker</Link>
        </>
      }
    >
      {sessionEndReason && <Banner tone="info">{REASONS[sessionEndReason]}</Banner>}
      {notice && <Banner tone="success">{notice}</Banner>}
      <LoginForm />
    </AuthLayout>
  );
}
