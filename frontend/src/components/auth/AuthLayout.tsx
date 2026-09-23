import type { ReactNode } from "react";
import { HeartPulse, MapPin, ShieldCheck } from "lucide-react";
import { brand } from "../../content/landing";
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

/** Two columns: brand panel on the left (hidden on small screens), form on the right. */
export function AuthLayout({ title, subtitle, children, footer, wide = false }: AuthLayoutProps) {
  return (
    <div className={styles.layout}>
      <aside className={styles.panel}>
        <Logo tone="light" />
        <div className={styles.pitch}>
          <p className={styles.tagline}>{brand.tagline}</p>
          <ul className={styles.points}>
            {points.map(({ icon: Icon, text }) => (
              <li key={text}>
                <Icon size={20} aria-hidden="true" />
                <span>{text}</span>
              </li>
            ))}
          </ul>
        </div>
      </aside>

      <main className={styles.main}>
        <div className={styles.mobileLogo}>
          <Logo />
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
