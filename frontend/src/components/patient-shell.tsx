import { type ReactNode, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppSidebar } from "@/components/app-sidebar";
import { authService, patientService } from "@/lib/api";

export function PatientShell({ children }: { children: ReactNode }) {
  const currentUser = authService.getCurrentUser();
  const { data: profile } = useQuery({ queryKey: ["patientProfile"], queryFn: patientService.getProfile });
  const user = useMemo(() => {
    const name = profile?.full_name || currentUser?.full_name || "Patient";
    return { name, email: profile?.email || currentUser?.email || "", initial: name.charAt(0).toUpperCase() };
  }, [profile, currentUser]);

  return (
    <div className="flex min-h-screen w-full bg-surface">
      <AppSidebar role="patient" user={user} />
      <main className="mx-auto w-full max-w-[1600px] flex-1 px-5 py-6 lg:px-8 lg:py-8">{children}</main>
    </div>
  );
}