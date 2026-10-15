import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { roles } from "../../../content/landing";
import { Container } from "../../ui/Container/Container";
import { BlurIn } from "../BlurIn/BlurIn";
import { Eyebrow } from "../Eyebrow/Eyebrow";
import { RoleArt } from "./RoleArt";
import styles from "./Roles.module.css";

export function Roles() {
  return (
    <section id={roles.id} className={styles.section} aria-labelledby={roles.headingId}>
      <Container>
        <BlurIn className={styles.header}>
          <Eyebrow>{roles.eyebrow}</Eyebrow>
          <h2 id={roles.headingId} className={styles.title}>
            {roles.heading}
          </h2>
          <p className={styles.body}>{roles.body}</p>
        </BlurIn>

        <ul className={styles.grid}>
          {roles.items.map((item, i) => (
            <BlurIn as="li" key={item.role} delay={(i + 1) as 1 | 2 | 3} className={styles.cell}>
              <Link to={item.href} className={styles.card}>
                <span className={styles.art}>
                  <RoleArt role={item.role} />
                </span>
                <span className={styles.who}>{item.who}</span>
                <h3 className={styles.cardTitle}>{item.title}</h3>
                <span className={styles.cardBody}>{item.body}</span>
                <span className={styles.cta}>
                  {item.cta}
                  <ArrowRight size={16} aria-hidden="true" />
                </span>
              </Link>
            </BlurIn>
          ))}
        </ul>
      </Container>
    </section>
  );
}
