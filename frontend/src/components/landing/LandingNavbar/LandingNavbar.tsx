import { useCallback, useEffect, useRef, useState } from "react";
import { Menu, X } from "lucide-react";
import { nav, routes } from "../../../content/landing";
import { Button } from "../../ui/Button/Button";
import { Container } from "../../ui/Container/Container";
import { Logo } from "../../ui/Logo/Logo";
import styles from "./LandingNavbar.module.css";

const FOCUSABLE = 'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function LandingNavbar() {
  const [open, setOpen] = useState(false);
  const toggleRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  const close = useCallback(() => {
    setOpen(false);
    toggleRef.current?.focus();
  }, []);

  // While the panel is open: trap Tab inside it, close on Escape, lock page scroll.
  useEffect(() => {
    if (!open) return;
    const panel = panelRef.current;
    if (!panel) return;

    const focusables = () => Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE));
    focusables()[0]?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        close();
        return;
      }
      if (event.key !== "Tab") return;
      const items = focusables();
      const first = items[0];
      const last = items[items.length - 1];
      if (!first || !last) return;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    const { overflow } = document.body.style;
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = overflow;
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open, close]);

  // Close the panel if the viewport grows past the mobile breakpoint.
  useEffect(() => {
    const query = window.matchMedia("(min-width: 1024px)");
    const onChange = () => query.matches && setOpen(false);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);

  return (
    <header className={styles.header}>
      <Container className={styles.inner}>
        <Logo />

        <nav aria-label={nav.label} className={styles.desktopNav}>
          <ul className={styles.links}>
            {nav.links.map((link) => (
              <li key={link.href}>
                <a href={link.href} className={styles.link}>
                  {link.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <div className={styles.actions}>
          <Button to={routes.login} variant="ghost">
            {nav.login}
          </Button>
          <Button to={routes.signup}>{nav.getStarted}</Button>
        </div>

        <button
          ref={toggleRef}
          type="button"
          className={styles.toggle}
          aria-label={nav.openMenu}
          aria-expanded={open}
          aria-controls="mobile-menu"
          onClick={() => setOpen(true)}
        >
          <Menu size={22} aria-hidden="true" />
        </button>
      </Container>

      {open && (
        <div className={styles.overlay} onClick={close}>
          <div
            ref={panelRef}
            id="mobile-menu"
            role="dialog"
            aria-modal="true"
            aria-label={nav.menuTitle}
            className={styles.panel}
            onClick={(event) => event.stopPropagation()}
          >
            <div className={styles.panelHeader}>
              <Logo />
              <button type="button" className={styles.toggle} aria-label={nav.closeMenu} onClick={close}>
                <X size={22} aria-hidden="true" />
              </button>
            </div>
            <nav aria-label={nav.label}>
              <ul className={styles.mobileLinks}>
                {nav.links.map((link) => (
                  <li key={link.href}>
                    <a href={link.href} className={styles.mobileLink} onClick={() => setOpen(false)}>
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </nav>
            <div className={styles.mobileActions}>
              <Button to={routes.signup} size="lg">
                {nav.getStarted}
              </Button>
              <Button to={routes.login} variant="secondary" size="lg">
                {nav.login}
              </Button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
