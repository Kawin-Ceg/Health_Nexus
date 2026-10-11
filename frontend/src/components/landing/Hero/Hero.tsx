import { ArrowRight, CircleCheck, Sparkles } from "lucide-react";
import { hero, routes } from "../../../content/landing";
import { Button } from "../../ui/Button/Button";
import { Container } from "../../ui/Container/Container";
import { BlurIn } from "../BlurIn/BlurIn";
import styles from "./Hero.module.css";
import { HeroArt } from "./HeroArt";

const words = (text: string) => text.split(" ").filter(Boolean);

export function Hero() {
  const lead = words(hero.heading.lead);
  const highlight = words(hero.heading.highlight);
  return (
    <section className={styles.hero} aria-labelledby={hero.headingId}>
      <HeroArt />
      <Container className={styles.inner}>
        <h1 id={hero.headingId} className={styles.title}>
          {lead.map((word, i) => (
            <span key={`l${i}`} className={styles.word}>
              {word}{" "}
            </span>
          ))}
          <span className={styles.highlight}>
            {highlight.map((word, i) => (
              <span key={`h${i}`} className={styles.word}>
                {word}{" "}
              </span>
            ))}
          </span>
        </h1>

        <div className={styles.ctas}>
          <Button to={routes.signup} size="lg">
            {hero.primaryCta}
            <ArrowRight size={18} aria-hidden="true" />
          </Button>
          <Button to={routes.phcSignup} size="lg" variant="secondary">
            {hero.secondaryCta}
          </Button>
        </div>

        <ul className={styles.trust}>
          {hero.trust.map((item) => (
            <li key={item}>
              <CircleCheck size={18} aria-hidden="true" />
              {item}
            </li>
          ))}
        </ul>

        <BlurIn className={styles.chatWrap}>
        <figure className={styles.chat} aria-label={hero.chat.label}>
          <p className={styles.chatSource}>{hero.chat.source}</p>
          <p className={styles.question}>{hero.chat.question}</p>
          <div className={styles.reply}>
            <span className={styles.avatar} aria-hidden="true">
              <Sparkles size={14} strokeWidth={2} />
            </span>
            <div>
              <p className={styles.answer}>{hero.chat.answer}</p>
              <p className={styles.reason}>{hero.chat.reason}</p>
            </div>
          </div>
          <figcaption className={styles.disclaimer}>{hero.chat.disclaimer}</figcaption>
        </figure>
        </BlurIn>
      </Container>
    </section>
  );
}
