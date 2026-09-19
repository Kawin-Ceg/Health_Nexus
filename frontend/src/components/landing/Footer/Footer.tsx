import { useId, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { brand, footer } from "../../../content/landing";
import { Button } from "../../ui/Button/Button";
import { Container } from "../../ui/Container/Container";
import { Logo } from "../../ui/Logo/Logo";
import styles from "./Footer.module.css";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function FooterLink({ href, label }: { href: string; label: string }) {
  // In-page anchors stay plain links; routes go through the router.
  return href.startsWith("#") ? (
    <a href={href} className={styles.link}>
      {label}
    </a>
  ) : (
    <Link to={href} className={styles.link}>
      {label}
    </Link>
  );
}

function Newsletter() {
  const { newsletter } = footer;
  const inputId = useId();
  const messageId = useId();
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "invalid" | "done">("idle");

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    setStatus(EMAIL_PATTERN.test(email.trim()) ? "done" : "invalid");
  };

  return (
    <form className={styles.newsletter} onSubmit={onSubmit} noValidate>
      <p className={styles.newsTitle}>{newsletter.title}</p>
      <p className={styles.newsBody}>{newsletter.body}</p>
      <label htmlFor={inputId} className={styles.label}>
        {newsletter.label}
      </label>
      <div className={styles.field}>
        <input
          id={inputId}
          type="email"
          autoComplete="email"
          className={styles.input}
          placeholder={newsletter.placeholder}
          value={email}
          onChange={(event) => {
            setEmail(event.target.value);
            if (status !== "idle") setStatus("idle");
          }}
          aria-invalid={status === "invalid"}
          aria-describedby={messageId}
        />
        <Button type="submit" variant="inverse">
          {newsletter.submit}
        </Button>
      </div>
      <p id={messageId} className={status === "invalid" ? styles.error : styles.success} aria-live="polite">
        {status === "invalid" && newsletter.invalid}
        {status === "done" && newsletter.success}
      </p>
    </form>
  );
}

export function Footer() {
  return (
    <footer className={styles.footer}>
      <Container>
        <div className={styles.top}>
          <div className={styles.brand}>
            <Logo tone="light" />
            <p className={styles.tagline}>{brand.tagline}</p>
          </div>

          <nav aria-label={footer.label} className={styles.columns}>
            {footer.columns.map((column) => (
              <div key={column.title}>
                <p className={styles.columnTitle}>{column.title}</p>
                <ul className={styles.list}>
                  {column.links.map((link) => (
                    <li key={link.label}>
                      <FooterLink {...link} />
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </nav>

          <Newsletter />
        </div>

        <div className={styles.bottom}>
          <p>{footer.copyright}</p>
          <ul className={styles.legal} aria-label={footer.legalLabel}>
            {footer.legal.map((link) => (
              <li key={link.href}>
                <FooterLink {...link} />
              </li>
            ))}
          </ul>
        </div>
      </Container>
    </footer>
  );
}
