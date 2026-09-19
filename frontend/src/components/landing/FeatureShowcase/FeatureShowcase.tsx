import { features } from "../../../content/landing";
import { Reveal } from "../../animations/Reveal/Reveal";
import { Container } from "../../ui/Container/Container";
import { Eyebrow } from "../Eyebrow/Eyebrow";
import styles from "./FeatureShowcase.module.css";

export function FeatureShowcase() {
  const { heading } = features;
  return (
    <section id={features.id} className={styles.section} aria-labelledby={features.headingId}>
      <Container>
        <Reveal className={styles.header}>
          <Eyebrow>{features.eyebrow}</Eyebrow>
          <h2 id={features.headingId} className={styles.title}>
            {heading.lead}
            <em>{heading.emphasis}</em>
            {heading.tail}
          </h2>
          <p className={styles.body}>{features.body}</p>
        </Reveal>

        <ul className={styles.grid}>
          {features.items.map(({ icon: Icon, title, body }, i) => (
            <Reveal as="li" key={title} delay={(i % 3) as 0 | 1 | 2} className={styles.cell}>
              {/* Inner card owns the hover motion so it never fights the reveal transform. */}
              <div className={styles.card}>
                <span className={styles.bloom} aria-hidden="true" />
                <span className={styles.icon}>
                  <Icon size={24} strokeWidth={1.75} aria-hidden />
                </span>
                <h3 className={styles.cardTitle}>{title}</h3>
                <p className={styles.cardBody}>{body}</p>
              </div>
            </Reveal>
          ))}
        </ul>
      </Container>
    </section>
  );
}
