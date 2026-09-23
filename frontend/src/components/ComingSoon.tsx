import { Construction } from "lucide-react";
import { AppHeader } from "./AppHeader";
import styles from "./ComingSoon.module.css";

/** Stands in for every page outside authentication and onboarding. */
export function ComingSoon({ title }: { title: string }) {
  return (
    <>
      <AppHeader />
      <main className={styles.main}>
        <span className={styles.icon}>
          <Construction size={28} aria-hidden="true" />
        </span>
        <h1>{title}</h1>
        <p>This area is coming in a later module.</p>
      </main>
    </>
  );
}
