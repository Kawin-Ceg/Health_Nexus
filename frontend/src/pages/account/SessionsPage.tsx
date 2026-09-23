import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Laptop } from "lucide-react";
import { AppHeader } from "../../components/AppHeader";
import { Banner } from "../../components/auth/Banner";
import { Button } from "../../components/ui/Button/Button";
import { Spinner } from "../../components/ui/Spinner/Spinner";
import { useAuth } from "../../context/AuthContext";
import { destinationFor } from "../../lib/routes";
import { errorMessage } from "../../services/api";
import { listSessions, revokeOtherSessions, revokeSession, type SessionInfo } from "../../services/auth";
import styles from "./SessionsPage.module.css";

const when = (iso: string) =>
  new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(iso));

export function SessionsPage() {
  const { user } = useAuth();
  const [sessions, setSessions] = useState<SessionInfo[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setSessions(await listSessions());
      setError(null);
    } catch (e) {
      setError(errorMessage(e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const run = async (key: string, action: () => Promise<unknown>) => {
    setBusy(key);
    try {
      await action();
    } catch (e) {
      setError(errorMessage(e));
    }
    await load();
    setBusy(null);
  };

  const others = sessions?.filter((s) => !s.is_current).length ?? 0;

  return (
    <>
      <AppHeader />
      <main className={styles.main}>
        {user && (
          <Link to={destinationFor(user)} className={styles.back}>
            Back
          </Link>
        )}
        <h1>Your sessions</h1>
        <p className={styles.lead}>Places where you are signed in. Sign out any you do not recognise.</p>

        {error && <Banner tone="error">{error}</Banner>}

        {!sessions && !error && (
          <p role="status" className={styles.lead}>
            <Spinner /> Loading
          </p>
        )}

        {sessions && (
          <>
            <ul className={styles.list}>
              {sessions.map((s) => (
                <li key={s.id} className={styles.item}>
                  <Laptop size={22} aria-hidden="true" />
                  <div className={styles.info}>
                    <strong>
                      {s.device_label ?? "Unknown device"}
                      {s.is_current && <span className={styles.current}>This device</span>}
                    </strong>
                    <span className={styles.meta}>
                      {s.ip_address ?? "Unknown IP"} · Last active {when(s.last_activity_at)}
                    </span>
                  </div>
                  {!s.is_current && (
                    <Button variant="secondary" onClick={() => void run(s.id, () => revokeSession(s.id))} loading={busy === s.id}>
                      Sign out
                    </Button>
                  )}
                </li>
              ))}
            </ul>
            {others > 0 && (
              <Button
                variant="secondary"
                onClick={() => void run("others", revokeOtherSessions)}
                loading={busy === "others"}
              >
                Sign out of all other sessions
              </Button>
            )}
          </>
        )}
      </main>
    </>
  );
}
