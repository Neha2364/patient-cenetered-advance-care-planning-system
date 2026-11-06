import { createFileRoute } from "@tanstack/react-router";
import { AdminShell } from "@/components/admin-shell";
import { authService } from "@/lib/api";

export const Route = createFileRoute("/admin-dashboard/settings")({
  head: () => ({ meta: [{ title: "Admin Settings — ACP Care" }] }),
  component: AdminSettingsPage,
});

function AdminSettingsPage() {
  const user = authService.getCurrentUser();

  return (
    <AdminShell>
      <div className="mx-auto max-w-lg space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Account Settings</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Your administrator account information.
          </p>
        </div>

        <div className="rounded-2xl border border-border bg-white p-6 shadow-sm space-y-4">
          <div className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2">
            {[
              ["Full Name", user?.full_name ?? "—"],
              ["Email", user?.email ?? "—"],
              ["Role", "Administrator"],
            ].map(([label, value]) => (
              <div key={label}>
                <div className="text-xs font-medium text-muted-foreground">{label}</div>
                <div className="mt-0.5 font-medium text-foreground">{value}</div>
              </div>
            ))}
          </div>

          <div className="rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-xs text-blue-800">
            To change your admin password or email, contact a system administrator or use the
            server-side provisioning script.
          </div>
        </div>
      </div>
    </AdminShell>
  );
}

