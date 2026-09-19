import { ArrowRight } from "lucide-react";
import { finalCta, routes } from "../../../content/landing";
import { Reveal } from "../../animations/Reveal/Reveal";
import { Button } from "../../ui/Button/Button";
import { Container } from "../../ui/Container/Container";
import { Eyebrow } from "../Eyebrow/Eyebrow";
import styles from "./FinalCta.module.css";

export function FinalCta() {
  const { heading } = finalCta;
  return (
    <section className={styles.section} aria-labelledby={finalCta.headingId}>
      <Container className={styles.layout}>
        <Reveal className={styles.copy}>
          <Eyebrow>{finalCta.eyebrow}</Eyebrow>
          <h2 id={finalCta.headingId} className={styles.title}>
            {heading.lead}
            <em>{heading.emphasis}</em>
            {heading.tail}
          </h2>
          <p className={styles.body}>{finalCta.body}</p>
          <Button to={routes.signup} size="lg" className={styles.cta}>
            {finalCta.cta}
            <ArrowRight size={18} aria-hidden="true" />
          </Button>
        </Reveal>

        <ul className={styles.benefits} aria-label={finalCta.benefitsLabel}>
          {finalCta.benefits.map(({ icon: Icon, title, body }, i) => (
            <Reveal as="li" key={title} delay={(i + 1) as 1 | 2 | 3 | 4} className={styles.benefit}>
              <Icon size={24} strokeWidth={1.75} aria-hidden />
              <h3 className={styles.benefitTitle}>{title}</h3>
              <p className={styles.benefitBody}>{body}</p>
            </Reveal>
          ))}
        </ul>
      </Container>
    </section>
  );
}
