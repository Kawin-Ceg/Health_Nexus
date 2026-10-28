import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { destinationFor } from "../lib/routes";
import { FullPageSpinner } from "./ui/Spinner/Spinner";

export function RedirectIfAuthenticated() {
  const { user, status } = useAuth();
  if (status === "loading") return <FullPageSpinner />;
  if (user) return <Navigate to={destinationFor(user)} replace />;
  return <Outlet />;
}
