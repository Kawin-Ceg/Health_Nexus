import { Doodle } from "../Doodle/Doodle";
import styles from "./HeroArt.module.css";

export function HeroArt() {
  return (
    <div className={styles.art}>
      <Doodle piece="network" className={styles.network} delay={2} ambient />
      <Doodle piece="botanical" className={styles.botanical} delay={3} />
      <Doodle piece="speckle" className={styles.speckle} delay={4} />
      <Doodle piece="beads" className={`${styles.beads} ${styles.tablet}`} />
      <Doodle piece="tissue" className={styles.tissue} delay={1} />
      <Doodle piece="tree" className={styles.tree} delay={2} />
      <Doodle piece="ecg" className={`${styles.ecg} ${styles.tablet}`} delay={1} />
      <Doodle piece="honeycomb" className={styles.honeycomb} delay={3} />
      <Doodle piece="radial" className={styles.radial} delay={4} />
    </div>
  );
}
