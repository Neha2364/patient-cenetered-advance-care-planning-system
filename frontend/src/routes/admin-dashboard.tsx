import { createFileRoute, Outlet, useRouterState } from "@tanstack/react-router";
import { AdminShell } from "@/components/admin-shell";

export const Route = createFileRoute("/admin-dashboard")({
  head: () => ({
    meta: [
      { title: "Admin Dashboard — ACP Care" },
      { name: "description", content: "ACP Care administration portal." },
    ],
  }),
  component: AdminDashboardLayout,
});

function AdminDashboardLayout() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  // For the index path, render the shell here wrapping Outlet
  // Child routes (doctors, patients, settings) wrap themselves
  if (pathname === "/admin-dashboard") {
    return (
      <AdminShell>
        <Outlet />
      </AdminShell>
    );
  }
  return <Outlet />;
}

