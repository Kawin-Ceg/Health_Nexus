import { SearchX } from "lucide-react";
import { Button } from "../../components/ui/Button/Button";
import { paths } from "../../lib/routes";
import styles from "./ErrorPage.module.css";

export function NotFound() {
  return (
    <main className={styles.page}>
      <span className={styles.icon}>
        <SearchX size={28} aria-hidden="true" />
      </span>
      <h1>Page not found</h1>
      <p>The page you are looking for does not exist or has moved.</p>
      <Button to={paths.home}>Go to the home page</Button>
    </main>
  );
}
