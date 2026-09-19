import { phone } from "../../../content/landing";
import styles from "./PhoneMockup.module.css";

const SPARK_BARS = 7;

/** CSS-drawn phone showing today's vitals. Purely decorative. */
export function PhoneMockup() {
  return (
    <div className={styles.phone} aria-hidden="true">
      <div className={styles.screen}>
        <div className={styles.notch} />
        <div className={styles.header}>
          <p className={styles.date}>{phone.date}</p>
          <p className={styles.greeting}>{phone.greeting}</p>
        </div>
        <div className={styles.tiles}>
          {phone.tiles.map(({ icon: Icon, label, value, unit, tone }) => (
            <div key={label} className={`${styles.tile} ${styles[tone]}`}>
              <span className={styles.tileIcon}>
                <Icon size={16} strokeWidth={2} />
              </span>
              <p className={styles.tileLabel}>{label}</p>
              <p className={styles.tileValue}>
                {value}
                {unit && <span className={styles.unit}>{unit}</span>}
              </p>
              <span className={styles.spark}>
                {Array.from({ length: SPARK_BARS }, (_, i) => (
                  <i key={i} />
                ))}
              </span>
            </div>
          ))}
        </div>
        <p className={styles.status}>{phone.status}</p>
      </div>
    </div>
  );
}
