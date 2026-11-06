import { type ReactNode, useEffect } from "react";
import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { authService } from "@/lib/api";

interface RequireAuthenticationProps {
  children: ReactNode;
  /** When provided, the signed-in user must have one of these roles. */
  allowedRoles?: string[];
}

/**
 * Guards a route against unauthenticated and (optionally) wrong-role access.
 *
 * Usage:
 *   <RequireAuthentication>…</RequireAuthentication>
 *   <RequireAuthentication allowedRoles={["doctor", "admin"]}>…</RequireAuthentication>
 *   <RequireAuthentication allowedRoles={["admin"]}>…</RequireAuthentication>
 */
export function RequireAuthentication({
  children,
  allowedRoles,
}: RequireAuthenticationProps) {
  const navigate = useNavigate();
  const user = authService.getCurrentUser();

  useEffect(() => {
    if (!user) {
      toast.error("Please create an account or sign in to continue.");
      navigate({ to: "/", replace: true });
      return;
    }

    if (allowedRoles && allowedRoles.length > 0) {
      if (!allowedRoles.includes(user.role)) {
        // Smart cross-role redirect based on the user's actual role
        if (user.role === "admin") {
          toast.error("Access denied. Redirecting to Admin Dashboard.");
          navigate({ to: "/admin-dashboard", replace: true });
        } else if (user.role === "doctor") {
          toast.error("Access denied. Redirecting to your Doctor Dashboard.");
          navigate({ to: "/doctor-dashboard", replace: true });
        } else if (user.role === "patient") {
          toast.error("Access denied. Redirecting to your Patient Dashboard.");
          navigate({ to: "/patient-dashboard", replace: true });
        } else {
          toast.error("Access denied.");
          navigate({ to: "/", replace: true });
        }
      }
    }
  }, [navigate, user, allowedRoles]);

  // Don't render children if there is no user or if the user's role is wrong
  if (!user) return null;
  if (allowedRoles && allowedRoles.length > 0 && !allowedRoles.includes(user.role)) {
    return null;
  }

  return <>{children}</>;
}
