import { ArrowRight, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";
import { privacy, routes } from "../../../content/landing";
import { Reveal } from "../../animations/Reveal/Reveal";
import { Container } from "../../ui/Container/Container";
import { Eyebrow } from "../Eyebrow/Eyebrow";
import styles from "./PrivacyBanner.module.css";

export function PrivacyBanner() {
  const { heading } = privacy;
  return (
    <section id={privacy.id} className={styles.section} aria-labelledby={privacy.headingId}>
      <Container>
        <Reveal className={styles.banner}>
          <span className={styles.icon}>
            <ShieldCheck size={32} strokeWidth={1.75} aria-hidden />
          </span>
          <div className={styles.copy}>
            <Eyebrow tone="light">{privacy.eyebrow}</Eyebrow>
            <h2 id={privacy.headingId} className={styles.title}>
              {heading.lead}
              <em>{heading.emphasis}</em>
              {heading.tail}
            </h2>
            <p className={styles.body}>{privacy.body}</p>
            <Link to={routes.privacy} className={styles.link}>
              {privacy.link}
              <ArrowRight size={16} aria-hidden="true" />
            </Link>
          </div>
        </Reveal>
      </Container>
    </section>
  );
}
