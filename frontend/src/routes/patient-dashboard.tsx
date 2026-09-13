import { createFileRoute, Outlet, useRouterState } from "@tanstack/react-router";
import { PatientShell } from "@/components/patient-shell";
import { authService } from "@/lib/api";
import { RequireAuthentication } from "@/components/require-authentication";

export const Route = createFileRoute("/patient-dashboard")({
  head: () => ({
    meta: [
      { title: "Patient Dashboard — ACP Care" },
      { name: "description", content: "Manage your Advance Care Planning journey." },
    ],
  }),
  component: PatientDashboardLayout,
});

function PatientDashboardLayout() {
  const pathname = useRouterState({ select: (state) => state.location.pathname });

  // The dashboard index needs the shared shell; child pages already provide the same shell.
  if (pathname !== "/patient-dashboard") {
    return <Outlet />;
  }

  return (
    <PatientShell>
      <Outlet />
    </PatientShell>
  );
}