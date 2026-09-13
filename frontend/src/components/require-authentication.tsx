import { type ReactNode, useEffect } from "react";
import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { authService } from "@/lib/api";

export function RequireAuthentication({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const user = authService.getCurrentUser();

  useEffect(() => {
    if (!user) {
      toast.error("Please create an account or sign in to continue.");
      navigate({ to: "/", replace: true });
    }
  }, [navigate, user]);

  return user ? <>{children}</> : null;
}