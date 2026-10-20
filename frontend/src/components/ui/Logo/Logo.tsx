import { Link } from "react-router-dom";
import { brand, routes } from "../../../content/landing";
import styles from "./Logo.module.css";

/**
 * The HealthNexus wordmark.
 *
 * The supplied artwork has near-black lettering, so it only reads on light
 * surfaces. A lightened copy is used on dark ones: `tone="light"` for panels
 * that are dark in both themes (the footer, the auth aside), and the CSS below
 * swaps automatically when the whole app is in dark mode. Both files are small
 * and cached, so rendering both and hiding one costs little.
 */
export function Logo({ tone = "default", compact = false }: { tone?: "default" | "light"; compact?: boolean }) {
  if (compact) {
    return (
      <Link to={routes.home} className={styles.logo} aria-label={brand.homeLabel}>
        <img src="/brand/icon.png" alt="" width={32} height={32} className={styles.icon} />
      </Link>
    );
  }
  return (
    <Link to={routes.home} className={styles.logo} aria-label={brand.homeLabel}>
      {tone === "default" && (
        <img src="/brand/wordmark.png" alt="" width={173} height={30} className={`${styles.mark} ${styles.onLight}`} />
      )}
      <img
        src="/brand/wordmark-light.png"
        alt=""
        width={173}
        height={30}
        className={`${styles.mark} ${tone === "light" ? "" : styles.onDark}`}
      />
    </Link>
  );
}
