import type { ReactNode } from "react";
import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";
import { paths } from "../../lib/routes";
import { ThemeToggle } from "../ui/ThemeToggle/ThemeToggle";
import { Logo } from "../ui/Logo/Logo";
import styles from "./AuthLayout.module.css";

interface AuthLayoutProps {
  title: string;
  subtitle?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  wide?: boolean;
}

export function AuthLayout({ title, subtitle, children, footer, wide = false }: AuthLayoutProps) {
  return (
    <div className={`landing ${styles.layout}`}>

      <header className={styles.topBar}>
        <Logo />
        <span className={styles.topActions}>
          <ThemeToggle className="grid h-11 w-11 shrink-0 place-items-center rounded-full border border-line bg-surface/70 text-ink-soft transition-colors hover:border-ink/30 hover:text-ink" />
          <Link to={paths.home} className={styles.back}>
            <ArrowLeft size={16} aria-hidden="true" />
            Back to home
          </Link>
        </span>
      </header>

      <main className={styles.main}>
        <div className={wide ? `${styles.card} ${styles.wide}` : styles.card}>
          <header className={styles.header}>
            <h1>{title}</h1>
            {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
          </header>
          {children}
          {footer && <div className={styles.footer}>{footer}</div>}
        </div>
        <p className={styles.note}>It explains; it doesn't diagnose. In an emergency, call 108.</p>
      </main>
    </div>
  );
}
