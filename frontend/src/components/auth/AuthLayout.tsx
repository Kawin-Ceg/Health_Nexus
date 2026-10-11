import type { ReactNode } from "react";
import { ArrowLeft, HeartPulse, MapPin, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";
import { paths } from "../../lib/routes";
import { Doodle } from "../landing/Doodle/Doodle";
import { Logo } from "../ui/Logo/Logo";
import styles from "./AuthLayout.module.css";

const points = [
  { icon: HeartPulse, text: "Track your vitals and see what is normal for you." },
  { icon: MapPin, text: "Stay linked to your own primary health centre." },
  { icon: ShieldCheck, text: "Your data stays private. You choose what is shared." },
];

interface AuthLayoutProps {
  title: string;
  subtitle?: ReactNode;
  children: ReactNode;
  /** Below the form: "No account? Sign up" and similar. */
  footer?: ReactNode;
  /** A wider form column for pages with more fields. */
  wide?: boolean;
}

/** Two columns: an illustrated brand panel on the left (hidden on small screens), the form on the right. */
export function AuthLayout({ title, subtitle, children, footer, wide = false }: AuthLayoutProps) {
  return (
    <div className={`landing ${styles.layout}`}>
      <aside className={styles.panel}>
        <Doodle piece="beads" className={styles.beads} />
        <Doodle piece="ecg" className={styles.ecg} delay={1} />
        <Doodle piece="tree" className={styles.tree} delay={2} />
        <Doodle piece="capsules" className={styles.capsules} delay={3} />
        <Logo />
        <div className={styles.pitch}>
          <p className={styles.tagline}>Your health and your community's, in one place.</p>
          <ul className={styles.points}>
            {points.map(({ icon: Icon, text }) => (
              <li key={text}>
                <span className={styles.pointIcon}>
                  <Icon size={16} aria-hidden="true" />
                </span>
                <span>{text}</span>
              </li>
            ))}
          </ul>
        </div>
        <p className={styles.note}>It explains; it doesn't diagnose. In an emergency, call 108.</p>
      </aside>

      <main className={styles.main}>
        <div className={styles.topBar}>
          <span className={styles.mobileLogo}>
            <Logo />
          </span>
          <Link to={paths.home} className={styles.back}>
            <ArrowLeft size={16} aria-hidden="true" />
            Back to home
          </Link>
        </div>
        <div className={wide ? `${styles.card} ${styles.wide}` : styles.card}>
          <header className={styles.header}>
            <h1>{title}</h1>
            {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
          </header>
          {children}
          {footer && <div className={styles.footer}>{footer}</div>}
        </div>
      </main>
    </div>
  );
}
