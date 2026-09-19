import { Link } from "react-router-dom";
import { brand, routes } from "../../../content/landing";
import styles from "./Logo.module.css";

/** Wordmark with a simple geometric mark. `tone="light"` is for dark panels. */
export function Logo({ tone = "default" }: { tone?: "default" | "light" }) {
  return (
    <Link to={routes.home} className={`${styles.logo} ${styles[tone]}`} aria-label={brand.homeLabel}>
      <span className={styles.mark} aria-hidden="true">
        <span className={styles.dot} />
      </span>
      <span className={styles.name}>{brand.name}</span>
    </Link>
  );
}
