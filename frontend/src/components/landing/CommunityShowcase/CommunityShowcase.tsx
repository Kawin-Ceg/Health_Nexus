import { community } from "../../../content/landing";
import { Container } from "../../ui/Container/Container";
import { Eyebrow } from "../Eyebrow/Eyebrow";
import { BlurIn } from "../BlurIn/BlurIn";
import { Doodle } from "../Doodle/Doodle";
import styles from "./CommunityShowcase.module.css";

export function CommunityShowcase() {
  const { exampleColumns: col } = community;
  return (
    <section id={community.id} className={styles.section} aria-labelledby={community.headingId}>
      <Doodle piece="radial" className={styles.radial} />
      <Doodle piece="tissue" className={styles.tissue} delay={2} />
      <Container className={styles.layout}>
        <div>
          <BlurIn>
            <Eyebrow>{community.eyebrow}</Eyebrow>
            <h2 id={community.headingId} className={styles.title}>
              {community.heading}
            </h2>
            <p className={styles.body}>{community.body}</p>
          </BlurIn>

          <ul className={styles.points}>
            {community.points.map(({ icon: Icon, title, body }) => (
              <li key={title} className={styles.point}>
                <span className={styles.pointIcon}>
                  <Icon size={20} strokeWidth={1.75} aria-hidden />
                </span>
                <div>
                  <h3 className={styles.pointTitle}>{title}</h3>
                  <p className={styles.pointBody}>{body}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <BlurIn delay={2} className={styles.example}>
          <table className={styles.table}>
            <caption className={styles.caption}>{community.exampleCaption}</caption>
            <thead>
              <tr>
                <th scope="col">{col.area}</th>
                <th scope="col">{col.citizens}</th>
                <th scope="col">{col.flagged}</th>
                <th scope="col">{col.status}</th>
              </tr>
            </thead>
            <tbody>
              {community.exampleRows.map((row) => (
                <tr key={row.area}>
                  <th scope="row">{row.area}</th>
                  <td>{row.citizens}</td>
                  <td>{row.flagged}</td>
                  <td className={row.status === "Typical" ? undefined : styles.attention}>{row.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </BlurIn>
      </Container>
    </section>
  );
}
