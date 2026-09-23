import type { ReactNode } from "react";
import { AlertCircle, CheckCircle2, Info } from "lucide-react";
import styles from "./Auth.module.css";

const icons = { error: AlertCircle, success: CheckCircle2, info: Info };

/** Errors are announced immediately (role="alert"); the rest politely (role="status"). */
export function Banner({ tone, children }: { tone: "error" | "success" | "info"; children: ReactNode }) {
  const Icon = icons[tone];
  return (
    <div className={`${styles.banner} ${styles[tone]}`} role={tone === "error" ? "alert" : "status"}>
      <Icon size={18} aria-hidden="true" />
      <div>{children}</div>
    </div>
  );
}
