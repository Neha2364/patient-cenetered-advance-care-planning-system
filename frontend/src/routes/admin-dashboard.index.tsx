import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Users, Stethoscope, UserCheck, UserX, ArrowRight, AlertTriangle } from "lucide-react";
import { AdminShell } from "@/components/admin-shell";
import { adminService } from "@/lib/api";

export const Route = createFileRoute("/admin-dashboard/")({
  head: () => ({ meta: [{ title: "Admin Dashboard — ACP Care" }] }),
  component: AdminDashboardIndex,
});

function StatCard({
  label,
  value,
  icon: Icon,
  color,
  delay,
}: {
  label: string;
  value: number | string;
  icon: React.ElementType;
  color: string;
  delay: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4 }}
      className="rounded-2xl border border-border bg-white p-6 shadow-sm"
    >
      <div className={`mb-4 inline-flex h-11 w-11 items-center justify-center rounded-xl ${color}`}>
        <Icon className="h-5 w-5 text-white" />
      </div>
      <div className="text-3xl font-bold text-foreground">{value}</div>
      <div className="mt-1 text-sm text-muted-foreground">{label}</div>
    </motion.div>
  );
}

function AdminDashboardIndex() {
  const { data: stats, isLoading, isError } = useQuery({
    queryKey: ["adminDashboard"],
    queryFn: adminService.getDashboard,
    refetchInterval: 30_000,
  });

  return (
    <AdminShell>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-foreground">Admin Dashboard</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            System overview for ACP Care platform management.
          </p>
        </div>

        {/* Stats Grid */}
        {isLoading && (
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="h-36 animate-pulse rounded-2xl bg-surface" />
            ))}
          </div>
        )}

        {isError && (
          <div className="flex items-center gap-3 rounded-2xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            Failed to load dashboard statistics. Please refresh.
          </div>
        )}

        {stats && (
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard label="Total Patients" value={stats.total_patients} icon={Users} color="bg-blue-500" delay={0} />
            <StatCard label="Total Doctors" value={stats.total_doctors} icon={Stethoscope} color="bg-teal-500" delay={0.06} />
            <StatCard label="Active Doctors" value={stats.active_doctors} icon={UserCheck} color="bg-green-500" delay={0.12} />
            <StatCard label="Inactive Doctors" value={stats.inactive_doctors} icon={UserX} color="bg-red-400" delay={0.18} />
          </div>
        )}

        {/* Quick actions */}
        <div className="grid gap-4 sm:grid-cols-2">
          <Link
            to="/admin-dashboard/doctors/add"
            className="group flex items-center justify-between rounded-2xl border border-border bg-white p-5 shadow-sm transition hover:border-primary/40 hover:shadow-md"
          >
            <div>
              <div className="font-semibold text-foreground">Add New Doctor</div>
              <div className="mt-0.5 text-sm text-muted-foreground">
                Create an authorized doctor account
              </div>
            </div>
            <ArrowRight className="h-4 w-4 text-muted-foreground transition group-hover:translate-x-1 group-hover:text-primary" />
          </Link>
          <Link
            to="/admin-dashboard/doctors"
            className="group flex items-center justify-between rounded-2xl border border-border bg-white p-5 shadow-sm transition hover:border-primary/40 hover:shadow-md"
          >
            <div>
              <div className="font-semibold text-foreground">Manage Doctors</div>
              <div className="mt-0.5 text-sm text-muted-foreground">
                View, edit, activate or deactivate doctors
              </div>
            </div>
            <ArrowRight className="h-4 w-4 text-muted-foreground transition group-hover:translate-x-1 group-hover:text-primary" />
          </Link>
          <Link
            to="/admin-dashboard/patients"
            className="group flex items-center justify-between rounded-2xl border border-border bg-white p-5 shadow-sm transition hover:border-primary/40 hover:shadow-md"
          >
            <div>
              <div className="font-semibold text-foreground">View Patients</div>
              <div className="mt-0.5 text-sm text-muted-foreground">
                Browse registered patient accounts
              </div>
            </div>
            <ArrowRight className="h-4 w-4 text-muted-foreground transition group-hover:translate-x-1 group-hover:text-primary" />
          </Link>
          <Link
            to="/admin-dashboard/settings"
            className="group flex items-center justify-between rounded-2xl border border-border bg-white p-5 shadow-sm transition hover:border-primary/40 hover:shadow-md"
          >
            <div>
              <div className="font-semibold text-foreground">Account Settings</div>
              <div className="mt-0.5 text-sm text-muted-foreground">
                Manage your admin account
              </div>
            </div>
            <ArrowRight className="h-4 w-4 text-muted-foreground transition group-hover:translate-x-1 group-hover:text-primary" />
          </Link>
        </div>
      </div>
    </AdminShell>
  );
}

