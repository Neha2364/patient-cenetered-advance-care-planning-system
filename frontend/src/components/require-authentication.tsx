import { type ReactNode, useEffect } from "react";
import { useNavigate, useRouterState } from "@tanstack/react-router";
import { toast } from "sonner";
import { authService } from "@/lib/api";

interface RequireAuthenticationProps {
  children: ReactNode;
  /** When provided, the signed-in user must have one of these roles. */
  allowedRoles?: string[];
}

/**
 * Guards a route against unauthenticated and (optionally) wrong-role access.
 * Also enforces mandatory first-login password changes for doctor accounts.
 *
 * Usage:
 *   <RequireAuthentication>…</RequireAuthentication>
 *   <RequireAuthentication allowedRoles={["doctor", "admin"]}>…</RequireAuthentication>
 *   <RequireAuthentication allowedRoles={["admin"]}>…</RequireAuthentication>
 */
export function RequireAuthentication({ children, allowedRoles }: RequireAuthenticationProps) {
  const navigate = useNavigate();
  const user = authService.getCurrentUser();
  const currentPath = useRouterState({ select: (r) => r.location.pathname });

  useEffect(() => {
    if (!user) {
      toast.error("Please create an account or sign in to continue.");
      if (typeof window !== "undefined") {
        const port = window.location.port;
        const path = window.location.pathname;
        if (port === "8081" || path.startsWith("/doctor-")) {
          navigate({ to: "/doctor-login", replace: true });
          return;
        }
        if (port === "8082" || path.startsWith("/admin-")) {
          navigate({ to: "/admin-login", replace: true });
          return;
        }
      }
      navigate({ to: "/", replace: true });
      return;
    }

    // MANDATORY FIRST-LOGIN PASSWORD CHANGE:
    // If a doctor must change their password, restrict navigation exclusively to the change-password page.
    if (user.role === "doctor" && user.must_change_password) {
      if (currentPath !== "/doctor-dashboard/change-password") {
        toast.info(
          "Password change required before accessing doctor dashboard or patient records.",
        );
        navigate({ to: "/doctor-dashboard/change-password", replace: true });
        return;
      }
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
          if (typeof window !== "undefined") {
            const port = window.location.port;
            if (port === "8081") {
              navigate({ to: "/doctor-login", replace: true });
              return;
            }
            if (port === "8082") {
              navigate({ to: "/admin-login", replace: true });
              return;
            }
          }
          navigate({ to: "/", replace: true });
        }
      }
    }
  }, [navigate, user, allowedRoles, currentPath]);

  // Don't render children if there is no user or if the user's role is wrong
  if (!user) return null;
  if (allowedRoles && allowedRoles.length > 0 && !allowedRoles.includes(user.role)) {
    return null;
  }
  // Don't render children for doctors if temporary password change is pending (unless on change-password page)
  if (
    user.role === "doctor" &&
    user.must_change_password &&
    currentPath !== "/doctor-dashboard/change-password"
  ) {
    return null;
  }

  return <>{children}</>;
}
