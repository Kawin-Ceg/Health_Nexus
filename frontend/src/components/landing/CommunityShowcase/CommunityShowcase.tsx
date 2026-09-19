import { community } from "../../../content/landing";
import { Reveal } from "../../animations/Reveal/Reveal";
import { Badge } from "../../ui/Badge/Badge";
import { Container } from "../../ui/Container/Container";
import { Eyebrow } from "../Eyebrow/Eyebrow";
import styles from "./CommunityShowcase.module.css";

export function CommunityShowcase() {
  const { heading } = community;
  return (
    <section id={community.id} className={styles.section} aria-labelledby={community.headingId}>
      <Container className={styles.layout}>
        <div>
          <Reveal>
            <Eyebrow>{community.eyebrow}</Eyebrow>
            <h2 id={community.headingId} className={styles.title}>
              {heading.lead}
              <em>{heading.emphasis}</em>
              {heading.tail}
            </h2>
            <p className={styles.body}>{community.body}</p>
          </Reveal>

          <ul className={styles.points}>
            {community.points.map(({ icon: Icon, title, body }, i) => (
              <Reveal as="li" key={title} delay={(i + 1) as 1 | 2 | 3} className={styles.point}>
                <span className={styles.pointIcon}>
                  <Icon size={20} strokeWidth={1.75} aria-hidden />
                </span>
                <div>
                  <h3 className={styles.pointTitle}>{title}</h3>
                  <p className={styles.pointBody}>{body}</p>
                </div>
              </Reveal>
            ))}
          </ul>
        </div>

        <Reveal delay={2} className={styles.map}>
          <div className={styles.mapTop}>
            <p className={styles.mapCaption}>{community.mapCaption}</p>
            <span className={styles.live} title={community.liveLabel}>
              <Badge tone="accent">
                <span className={styles.liveDot} aria-hidden="true" />
                {community.live}
              </Badge>
            </span>
          </div>
          <div className={styles.field} aria-hidden="true">
            {community.localities.map((name) => (
              <span key={name} className={styles.area}>
                <span className={styles.ring} />
                <span className={styles.areaName}>{name}</span>
              </span>
            ))}
          </div>
        </Reveal>
      </Container>
    </section>
  );
}
