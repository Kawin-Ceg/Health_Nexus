import { ArrowRight } from "lucide-react";
import { finalCta, routes } from "../../../content/landing";
import { Button } from "../../ui/Button/Button";
import { Container } from "../../ui/Container/Container";
import { BlurIn } from "../BlurIn/BlurIn";
import { Doodle } from "../Doodle/Doodle";
import { Eyebrow } from "../Eyebrow/Eyebrow";
import styles from "./FinalCta.module.css";

export function FinalCta() {
  return (
    <section className={styles.section} aria-labelledby={finalCta.headingId}>
      <Doodle piece="tree" className={styles.tree} />
      <Doodle piece="ecg" className={styles.ecg} delay={1} />
      <Doodle piece="capsules" className={styles.capsules} delay={2} />
      <Container>
        <BlurIn className={styles.inner}>
          <Eyebrow>{finalCta.eyebrow}</Eyebrow>
          <h2 id={finalCta.headingId} className={styles.title}>
            {finalCta.heading}
          </h2>
          <p className={styles.body}>{finalCta.body}</p>
          <div className={styles.ctas}>
            <Button to={routes.signup} size="lg">
              {finalCta.cta}
              <ArrowRight size={18} aria-hidden="true" />
            </Button>
            <Button to={routes.phcSignup} size="lg" variant="secondary">
              {finalCta.secondaryCta}
            </Button>
          </div>
          <p className={styles.note}>{finalCta.note}</p>
        </BlurIn>
      </Container>
    </section>
  );
}
