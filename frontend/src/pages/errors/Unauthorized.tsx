import { Navigate } from "react-router-dom";
import { ShieldAlert } from "lucide-react";
import { Button } from "../../components/ui/Button/Button";
import { useAuth } from "../../context/AuthContext";
import { destinationFor, paths } from "../../lib/routes";
import styles from "./ErrorPage.module.css";

export function Unauthorized() {
  const { user, status } = useAuth();
  if (status === "authenticated" && !user) return <Navigate to={paths.login} replace />;
  return (
    <main className={styles.page}>
      <span className={styles.icon}>
        <ShieldAlert size={28} aria-hidden="true" />
      </span>
      <h1>You do not have access to that page</h1>
      <p>Your account type cannot open it. If you think this is a mistake, contact your administrator.</p>
      <Button to={user ? destinationFor(user) : paths.home}>{user ? "Go to my home page" : "Go to the home page"}</Button>
    </main>
  );
}
