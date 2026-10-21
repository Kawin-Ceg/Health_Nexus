import { ArrowRight, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";
import { privacy, routes } from "../../../content/landing";
import { Container } from "../../ui/Container/Container";
import { Eyebrow } from "../Eyebrow/Eyebrow";
import { BlurIn } from "../BlurIn/BlurIn";
import { Doodle } from "../Doodle/Doodle";
import styles from "./PrivacyBanner.module.css";

export function PrivacyBanner() {
  return (
    <section id={privacy.id} className={styles.section} aria-labelledby={privacy.headingId}>
      <Doodle piece="beads" className={styles.beads} />
      <Container>
        <BlurIn className={styles.banner}>
          <span className={styles.icon}>
            <ShieldCheck size={28} strokeWidth={1.75} aria-hidden />
          </span>
          <div className={styles.copy}>
            <Eyebrow>{privacy.eyebrow}</Eyebrow>
            <h2 id={privacy.headingId} className={styles.title}>
              {privacy.heading}
            </h2>
            <ul className={styles.points}>
              {privacy.points.map((point) => (
                <li key={point}>{point}</li>
              ))}
            </ul>
            <Link to={routes.privacy} className={styles.link}>
              {privacy.link}
              <ArrowRight size={16} aria-hidden="true" />
            </Link>
          </div>
        </BlurIn>
      </Container>
    </section>
  );
}
