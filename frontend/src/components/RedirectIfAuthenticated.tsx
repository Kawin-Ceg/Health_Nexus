import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { destinationFor } from "../lib/routes";
import { FullPageSpinner } from "./ui/Spinner/Spinner";

/** Landing, login and signup are for signed-out visitors; anyone else goes where they belong. */
export function RedirectIfAuthenticated() {
  const { user, status } = useAuth();
  if (status === "loading") return <FullPageSpinner />;
  if (user) return <Navigate to={destinationFor(user)} replace />;
  return <Outlet />;
}
