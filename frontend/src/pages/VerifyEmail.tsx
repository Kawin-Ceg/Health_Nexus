import { useEffect, useRef, useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { CheckCircle2, MailCheck } from "lucide-react";
import { AuthLayout } from "../components/auth/AuthLayout";
import { Banner } from "../components/auth/Banner";
import { Button } from "../components/ui/Button/Button";
import { Spinner } from "../components/ui/Spinner/Spinner";
import { useAuth } from "../context/AuthContext";
import { destinationFor, paths } from "../lib/routes";
import { errorMessage, retryAfterSeconds } from "../services/api";
import { sendVerificationEmail, verifyEmail, type User } from "../services/auth";
import styles from "../components/auth/Auth.module.css";

type Redeem = "idle" | "working" | "done" | "failed";

/**
 * Public on purpose: people open the link on a phone or another browser with no session.
 * With a token it redeems it; without one it is the "check your inbox" screen.
 */
export function VerifyEmail() {
  const [params, setParams] = useSearchParams();
  // Captured once, then removed from the address bar so it does not linger in history.
  const [token] = useState(() => params.get("token"));
  const { user, status, refreshUser } = useAuth();
  const navigate = useNavigate();

  const [redeem, setRedeem] = useState<Redeem>(token ? "working" : "idle");
  const [redeemError, setRedeemError] = useState<string | null>(null);
  const started = useRef(false);

  useEffect(() => {
    if (!token || started.current) return; // the ref keeps StrictMode from spending a single-use token twice
    started.current = true;
    setParams({}, { replace: true });
    verifyEmail(token)
      .then(async () => {
        await refreshUser(); // a no-op when there is no session on this device
        setRedeem("done");
      })
      .catch((error) => {
        setRedeemError(errorMessage(error));
        setRedeem("failed");
      });
  }, [token, setParams, refreshUser]);

  if (token) {
    if (redeem === "working") {
      return (
        <AuthLayout title="Verifying your email">
          <p className={styles.muted} role="status">
            <Spinner /> One moment
          </p>
        </AuthLayout>
      );
    }
    if (redeem === "done") {
      return (
        <AuthLayout title="Email verified" subtitle="Thank you. Your address is confirmed.">
          <div className={styles.stack}>
            <span className={styles.badge}>
              <CheckCircle2 size={28} aria-hidden="true" />
            </span>
            {user ? (
              <Button size="lg" onClick={() => navigate(destinationFor(user), { replace: true })}>
                Continue
              </Button>
            ) : (
              <Button to={paths.login} size="lg">
                Sign in
              </Button>
            )}
          </div>
        </AuthLayout>
      );
    }
    return (
      <AuthLayout title="This link did not work" footer={<Link to={paths.login}>Back to sign in</Link>}>
        <div className={styles.stack}>
          <Banner tone="error">{redeemError}</Banner>
          <p className={styles.muted}>
            Links work once and expire after 24 hours. If you already used it, your email is verified: just sign in.
            Otherwise sign in and we will send a new one.
          </p>
          <Button to={paths.login}>Sign in</Button>
        </div>
      </AuthLayout>
    );
  }

  if (status === "loading") return null;
  if (!user) {
    return (
      <AuthLayout title="Verify your email" footer={<Link to={paths.login}>Back to sign in</Link>}>
        <div className={styles.stack}>
          <p>Open the link we emailed you to confirm your address. Need a new link? Sign in and request one.</p>
          <Button to={paths.login}>Sign in</Button>
        </div>
      </AuthLayout>
    );
  }
  if (user.is_verified) return <Navigate to={destinationFor(user)} replace />;
  return <CheckInbox email={user.email} onContinue={refreshUser} />;
}

function CheckInbox({ email, onContinue }: { email: string; onContinue: () => Promise<User | null> }) {
  const { logout } = useAuth();
  const [sending, setSending] = useState(false);
  const [message, setMessage] = useState<{ tone: "success" | "error"; text: string } | null>(null);
  const [wait, setWait] = useState(0);
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    if (wait <= 0) return;
    const timer = setTimeout(() => setWait((w) => w - 1), 1000);
    return () => clearTimeout(timer);
  }, [wait]);

  const resend = async () => {
    setSending(true);
    setMessage(null);
    try {
      const { detail } = await sendVerificationEmail();
      setMessage({ tone: "success", text: detail });
      setWait(60);
    } catch (error) {
      const seconds = retryAfterSeconds(error);
      if (seconds) setWait(seconds);
      setMessage({ tone: "error", text: errorMessage(error) });
    } finally {
      setSending(false);
    }
  };

  const check = async () => {
    setChecking(true);
    const fresh = await onContinue();
    setChecking(false);
    if (!fresh?.is_verified) {
      setMessage({ tone: "error", text: "Not verified yet. Open the link in your email, then try again." });
    }
  };

  return (
    <AuthLayout
      title="Check your inbox"
      subtitle={
        <>
          We sent a verification link to <strong>{email}</strong>. It works once and expires in 24 hours.
        </>
      }
      footer={
        <button type="button" className={styles.link} onClick={() => void logout()}>
          Sign out
        </button>
      }
    >
      <div className={styles.stack}>
        <span className={styles.badge}>
          <MailCheck size={28} aria-hidden="true" />
        </span>
        {message && <Banner tone={message.tone}>{message.text}</Banner>}
        <div className={styles.actions}>
          <Button size="lg" onClick={check} loading={checking}>
            I have verified my email
          </Button>
          <Button size="lg" variant="secondary" onClick={resend} loading={sending} disabled={wait > 0}>
            {wait > 0 ? `Resend in ${wait}s` : "Resend email"}
          </Button>
        </div>
        <p className={styles.muted}>You can open the link on any device. It does not need to be this one.</p>
      </div>
    </AuthLayout>
  );
}
