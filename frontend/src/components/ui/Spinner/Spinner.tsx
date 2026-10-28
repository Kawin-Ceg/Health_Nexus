import styles from "./Spinner.module.css";

export function Spinner({ className }: { className?: string }) {
  return <span className={className ? `${styles.spinner} ${className}` : styles.spinner} aria-hidden="true" />;
}

export function FullPageSpinner({ label = "Loading" }: { label?: string }) {
  return (
    <div className={styles.page} role="status">
      <Spinner className={styles.large} />
      <span className="visually-hidden">{label}</span>
    </div>
  );
}
