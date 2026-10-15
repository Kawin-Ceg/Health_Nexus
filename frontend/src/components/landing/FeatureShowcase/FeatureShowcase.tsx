import { useState } from "react";
import { features } from "../../../content/landing";
import { Container } from "../../ui/Container/Container";
import { BlurIn } from "../BlurIn/BlurIn";
import { Eyebrow } from "../Eyebrow/Eyebrow";
import { Doodle } from "../Doodle/Doodle";
import styles from "./FeatureShowcase.module.css";

const PLACES = ["nw", "ne", "w", "e", "sw", "se"] as const;
const SPOKES: Record<(typeof PLACES)[number], [number, number]> = {
  nw: [20, 16],
  ne: [80, 16],
  w: [14, 50],
  e: [86, 50],
  sw: [20, 84],
  se: [80, 84],
};

export function FeatureShowcase() {
  const [open, setOpen] = useState(false);
  const reveal = () => setOpen(true);

  return (
    <section id={features.id} className={styles.section} aria-labelledby={features.headingId}>
      <Doodle piece="helix" className={styles.helix} />
      <Doodle piece="capsules" className={styles.capsules} delay={2} />
      <Doodle piece="flask" className={styles.flask} delay={1} />
      <Doodle piece="speckle" className={styles.speckle} delay={3} />
      <Container>
        <BlurIn className={styles.header}>
          <Eyebrow>{features.eyebrow}</Eyebrow>
          <h2 id={features.headingId} className={styles.title}>
            {features.heading}
          </h2>
          <p className={styles.body}>{features.body}</p>
        </BlurIn>

        <div className={styles.hubLayout} data-open={open}>
          <svg className={styles.spokes} viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
            {PLACES.map((place) => (
              <line key={place} x1="50" y1="50" x2={SPOKES[place][0]} y2={SPOKES[place][1]} vectorEffect="non-scaling-stroke" />
            ))}
          </svg>

          <button
            type="button"
            className={styles.hub}
            aria-expanded={open}
            aria-controls="feature-list"
            onMouseEnter={reveal}
            onFocus={reveal}
            onClick={() => setOpen((o) => !o)}
          >
            <img src="/brand/icon.png" alt="" width={44} height={44} />
            <span className={styles.hubTitle}>{features.hub.title}</span>
            <span className={styles.hubBody}>{features.hub.body}</span>
            <span className={styles.hint}>{features.hub.hint}</span>
          </button>

          <ul id="feature-list" className={styles.items} role="list">
            {features.items.map(({ icon: Icon, title, body }, i) => (
              <li key={title} className={`${styles.item} ${styles[PLACES[i]]}`}>
                <span className={styles.icon}>
                  <Icon size={20} strokeWidth={1.75} aria-hidden />
                </span>
                <div>
                  <h3 className={styles.itemTitle}>{title}</h3>
                  <p className={styles.itemBody}>{body}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </Container>
    </section>
  );
}
