import { type ReactNode, useMemo } from "react";
import { AppSidebar } from "@/components/app-sidebar";
import { RequireAuthentication } from "@/components/require-authentication";
import { authService } from "@/lib/api";

export function DoctorPageShell({ children }: { children: ReactNode }) {
  const currentUser = authService.getCurrentUser();
  const doctor = useMemo(() => {
    const name = currentUser?.full_name || "Doctor";
    return { name, email: currentUser?.email || "", initial: name.charAt(0).toUpperCase() };
  }, [currentUser]);

  return <RequireAuthentication><div className="flex min-h-screen w-full bg-surface"><AppSidebar role="doctor" user={doctor} /><main className="mx-auto w-full max-w-[1600px] flex-1 px-5 py-6 lg:px-8 lg:py-8">{children}</main></div></RequireAuthentication>;
}