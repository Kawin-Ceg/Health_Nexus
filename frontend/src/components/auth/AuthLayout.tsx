import type { ReactNode } from "react";
import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";
import { paths } from "../../lib/routes";
import { Doodle } from "../landing/Doodle/Doodle";
import { SoundToggle } from "../landing/SoundToggle/SoundToggle";
import { ThemeToggle } from "../ui/ThemeToggle/ThemeToggle";
import { Logo } from "../ui/Logo/Logo";
import styles from "./AuthLayout.module.css";

interface AuthLayoutProps {
  title: string;
  subtitle?: ReactNode;
  children: ReactNode;
  /** Below the form: "No account? Sign up" and similar. */
  footer?: ReactNode;
  /** A wider form column for pages with more fields. */
  wide?: boolean;
}

/** One centred card on the cream page, with the illustrations around the edges. */
export function AuthLayout({ title, subtitle, children, footer, wide = false }: AuthLayoutProps) {
  return (
    <div className={`landing ${styles.layout}`}>
      <Doodle piece="network" className={styles.network} ambient />
      <Doodle piece="beads" className={styles.beads} />
      <Doodle piece="botanical" className={styles.botanical} delay={2} />
      <Doodle piece="microbe" className={styles.microbe} delay={1} />
      <Doodle piece="helix" className={styles.helix} delay={3} />
      <Doodle piece="tissue" className={styles.tissue} delay={1} />
      <Doodle piece="tree" className={styles.tree} delay={2} />
      <Doodle piece="ecg" className={styles.ecg} delay={1} />
      <Doodle piece="speckle" className={styles.speckle} delay={3} />
      <Doodle piece="coral" className={styles.coral} delay={2} />
      <Doodle piece="flask" className={styles.flask} delay={4} />
      <Doodle piece="capsules" className={styles.capsules} delay={3} />
      <Doodle piece="radial" className={styles.radial} delay={4} />

      <header className={styles.topBar}>
        <Logo />
        <span className={styles.topActions}>
          <ThemeToggle className="grid h-11 w-11 shrink-0 place-items-center rounded-full border border-line bg-surface/70 text-ink-soft transition-colors hover:border-ink/30 hover:text-ink" />
          <SoundToggle />
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
