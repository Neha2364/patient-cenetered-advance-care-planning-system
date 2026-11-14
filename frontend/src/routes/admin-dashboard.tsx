import { createFileRoute, Outlet } from "@tanstack/react-router";
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
  return (
    <AdminShell>
      <Outlet />
    </AdminShell>
  );
}

