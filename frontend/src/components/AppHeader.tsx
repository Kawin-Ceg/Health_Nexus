import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { paths } from "../lib/routes";
import { Button } from "./ui/Button/Button";
import { Logo } from "./ui/Logo/Logo";
import { ThemeToggle } from "./ui/ThemeToggle/ThemeToggle";
import styles from "./AppHeader.module.css";

/** Minimal signed-in header: who you are, your sessions, sign out. */
export function AppHeader() {
  const { user, logout } = useAuth();
  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <Logo />
        <nav className={styles.nav} aria-label="Account">
          {user && <span className={styles.who}>{user.name}</span>}
          <ThemeToggle className="grid h-11 w-11 shrink-0 place-items-center rounded-full border border-line bg-surface/70 text-ink-soft transition-colors hover:border-ink/30 hover:text-ink" />
          <Link to={paths.sessions} className={styles.link}>
            Sessions
          </Link>
          <Button variant="secondary" onClick={() => void logout()}>
            Sign out
          </Button>
        </nav>
      </div>
    </header>
  );
}
