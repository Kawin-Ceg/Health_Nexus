import type { ReactNode } from "react";
import styles from "./Badge.module.css";

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "accent" | "brand" }) {
  return <span className={`${styles.badge} ${styles[tone]}`}>{children}</span>;
}
