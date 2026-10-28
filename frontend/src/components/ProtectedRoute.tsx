import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { destinationFor, paths } from "../lib/routes";
import type { Role } from "../services/auth";
import { FullPageSpinner } from "./ui/Spinner/Spinner";

interface Props {
  allowedRoles: Role[];
  allowUnverified?: boolean;
  allowIncompleteProfile?: boolean;
}

export function ProtectedRoute({ allowedRoles, allowUnverified = false, allowIncompleteProfile = false }: Props) {
  const { user, status } = useAuth();
  const location = useLocation();

  if (status === "loading") return <FullPageSpinner />;
  if (!user) return <Navigate to={paths.login} replace state={{ from: location.pathname }} />;
  if (!allowedRoles.includes(user.role)) return <Navigate to={paths.unauthorized} replace />;

  if (!allowUnverified && !user.is_verified) return <Navigate to={paths.verifyEmail} replace />;
  if (user.role === "user" && !user.profile_completed && !allowIncompleteProfile && user.is_verified) {
    return <Navigate to={destinationFor(user)} replace />;
  }
  return <Outlet />;
}
