import { ArrowRight } from "lucide-react";
import { finalCta, routes } from "../../../content/landing";
import { Button } from "../../ui/Button/Button";
import { Container } from "../../ui/Container/Container";
import { BlurIn } from "../BlurIn/BlurIn";
import { Doodle } from "../Doodle/Doodle";
import styles from "./FinalCta.module.css";

export function FinalCta() {
  return (
    <section className={styles.section} aria-labelledby={finalCta.headingId}>
      <Doodle piece="network" className={styles.network} ambient />
      <Container>
        <BlurIn className={styles.inner}>
          <h2 id={finalCta.headingId} className={styles.title}>
            {finalCta.heading.lead}
            <br />
            {finalCta.heading.rest}
          </h2>
          <div className={styles.ctas}>
            <Button to={routes.signup} size="lg" variant="secondary">
              {finalCta.cta}
              <ArrowRight size={18} aria-hidden="true" />
            </Button>
            <Button to={routes.phcSignup} size="lg" variant="secondary">
              {finalCta.secondaryCta}
              <ArrowRight size={18} aria-hidden="true" />
            </Button>
          </div>
          <p className={styles.note}>{finalCta.note}</p>
        </BlurIn>
      </Container>
    </section>
  );
}
