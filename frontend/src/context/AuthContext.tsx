import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { registerAuthHandlers, setAccessToken, type SessionEndReason } from "../services/api";
import { clearDrafts } from "../lib/onboardingDraft";
import * as authApi from "../services/auth";
import type { User } from "../services/auth";

type Status = "loading" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  user: User | null;
  status: Status;
  /** Set when a session died on its own (idle for 48h, expired), so the login page can say why. Cleared by the next login. */
  sessionEndReason: SessionEndReason | null;
  login: (email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  /** Re-reads /auth/me, e.g. after verifying an email or finishing onboarding. */
  refreshUser: () => Promise<User | null>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<Status>("loading");
  const [sessionEndReason, setSessionEndReason] = useState<SessionEndReason | null>(null);

  useEffect(() => {
    registerAuthHandlers({
      onRefreshed: (fresh) => {
        setUser(fresh);
        setStatus("authenticated");
      },
      onSessionEnded: (reason) => {
        clearDrafts();
        setUser(null);
        setStatus("unauthenticated");
        setSessionEndReason(reason);
      },
    });
    // Restore the session once, from the httpOnly cookie. refreshSession is
    // single-flight, so StrictMode's second effect run shares this request.
    authApi.restoreSession().catch(() => setStatus((s) => (s === "loading" ? "unauthenticated" : s)));
    return () => registerAuthHandlers(null);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { user: signedIn } = await authApi.login(email, password);
    setUser(signedIn);
    setStatus("authenticated");
    setSessionEndReason(null);
    return signedIn;
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // Signing out locally must work even if the request fails.
    }
    setAccessToken(null);
    clearDrafts(); // health answers must not outlive the session on a shared device
    setUser(null);
    setStatus("unauthenticated");
    setSessionEndReason(null);
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const fresh = await authApi.fetchMe();
      setUser(fresh);
      return fresh;
    } catch {
      return null;
    }
  }, []);

  const value = useMemo(
    () => ({ user, status, sessionEndReason, login, logout, refreshUser }),
    [user, status, sessionEndReason, login, logout, refreshUser],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
