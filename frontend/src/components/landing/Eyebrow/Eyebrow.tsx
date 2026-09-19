import type { ReactNode } from "react";
import styles from "./Eyebrow.module.css";

/** Small uppercase label above a section heading. */
export function Eyebrow({ children, tone = "default" }: { children: ReactNode; tone?: "default" | "light" }) {
  return <p className={`${styles.eyebrow} ${styles[tone]}`}>{children}</p>;
}
