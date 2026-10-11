import { Link, useLocation } from "react-router-dom";
import { brand, footer, routes } from "../../../content/landing";
import { Container } from "../../ui/Container/Container";
import { Logo } from "../../ui/Logo/Logo";
import { Doodle } from "../Doodle/Doodle";
import styles from "./Footer.module.css";

function FooterLink({ href, label }: { href: string; label: string }) {
  const onHome = useLocation().pathname === routes.home;
  // In-page anchors stay plain links; routes go through the router.
  return href.startsWith("#") ? (
    <a href={onHome ? href : routes.home + href} className={styles.link}>
      {label}
    </a>
  ) : (
    <Link to={href} className={styles.link}>
      {label}
    </Link>
  );
}

export function Footer() {
  return (
    <footer className={styles.footer}>
      <Doodle piece="helix" className={styles.helix} />
      <Doodle piece="beads" className={styles.beads} delay={1} />
      <Container>
        <div className={styles.top}>
          <div className={styles.brand}>
            <Logo />
            <p className={styles.statement}>{footer.statement}</p>
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
            <div>
              <p className={styles.columnTitle}>{footer.legalLabel}</p>
              <ul className={styles.list}>
                {footer.legal.map((link) => (
                  <li key={link.href}>
                    <FooterLink {...link} />
                  </li>
                ))}
              </ul>
            </div>
          </nav>
        </div>

        <div className={styles.bottom}>
          <p>{footer.copyright}</p>
          <p className={styles.emergency}>{footer.emergency}</p>
        </div>
      </Container>
    </footer>
  );
}
