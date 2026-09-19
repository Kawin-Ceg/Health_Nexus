import type { ReactNode } from "react";
import styles from "./Container.module.css";

export function Container({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={className ? `${styles.container} ${className}` : styles.container}>{children}</div>;
}
