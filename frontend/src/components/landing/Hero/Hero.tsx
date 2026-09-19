import { ArrowRight, Sparkles, Watch } from "lucide-react";
import { hero, routes } from "../../../content/landing";
import { Reveal } from "../../animations/Reveal/Reveal";
import { Button } from "../../ui/Button/Button";
import { Container } from "../../ui/Container/Container";
import { Eyebrow } from "../Eyebrow/Eyebrow";
import { PhoneMockup } from "../PhoneMockup/PhoneMockup";
import styles from "./Hero.module.css";

export function Hero() {
  const { heading } = hero;
  return (
    <section className={styles.hero} aria-labelledby={hero.headingId}>
      <Container>
        <div className={styles.split}>
          <div className={styles.copy}>
            <Eyebrow>{hero.eyebrow}</Eyebrow>
            <h1 id={hero.headingId} className={styles.title}>
              {heading.lead}
              <em>{heading.emphasis}</em>
              {heading.tail}
            </h1>
            <p className={styles.body}>{hero.body}</p>
            <div className={styles.ctas}>
              <Button to={routes.signup} size="lg">
                {hero.primaryCta}
                <ArrowRight size={18} aria-hidden="true" />
              </Button>
              <Button to={routes.phcSignup} size="lg" variant="secondary">
                {hero.secondaryCta}
              </Button>
            </div>

            <figure className={styles.chat} aria-label={hero.chat.label}>
              <p className={styles.chatSource}>
                <Watch size={14} strokeWidth={2} aria-hidden />
                {hero.chat.source}
              </p>
              <p className={styles.question}>{hero.chat.question}</p>
              <div className={styles.replySlot}>
                <span className={styles.typing} aria-hidden="true" title={hero.chat.typing}>
                  <i />
                  <i />
                  <i />
                </span>
                <div className={styles.reply}>
                  <span className={styles.avatar} aria-hidden="true">
                    <Sparkles size={14} strokeWidth={2} />
                  </span>
                  <div>
                    <p className={styles.answer}>{hero.chat.answer}</p>
                    <p className={styles.reason}>{hero.chat.reason}</p>
                  </div>
                </div>
              </div>
            </figure>
          </div>

          <div className={styles.visual}>
            <PhoneMockup />
          </div>
        </div>

        <ul className={styles.pillars} aria-label={hero.pillarsLabel}>
          {hero.pillars.map(({ icon: Icon, title, body }, i) => (
            <Reveal as="li" key={title} delay={i as 0 | 1 | 2 | 3} className={styles.pillar}>
              <span className={styles.pillarIcon}>
                <Icon size={22} strokeWidth={1.75} aria-hidden />
              </span>
              <h2 className={styles.pillarTitle}>{title}</h2>
              <p className={styles.pillarBody}>{body}</p>
            </Reveal>
          ))}
        </ul>
      </Container>
    </section>
  );
}
