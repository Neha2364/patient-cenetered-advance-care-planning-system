import { createFileRoute, Outlet, useRouterState, Link } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Search,
  UserPlus,
  CheckCircle,
  XCircle,
  Eye,
  Pencil,
  AlertTriangle,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { adminService } from "@/lib/api";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/admin-dashboard/doctors")({
  head: () => ({ meta: [{ title: "Manage Doctors — ACP Care Admin" }] }),
  component: DoctorsLayout,
});

function DoctorsLayout() {
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const isIndex =
    pathname === "/admin-dashboard/doctors" || pathname === "/admin-dashboard/doctors/";
  return isIndex ? <ManageDoctorsPage /> : <Outlet />;
}

function ManageDoctorsPage() {
  const [search, setSearch] = useState("");
  const qc = useQueryClient();

  const {
    data: doctors,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["adminDoctors", search],
    queryFn: () => adminService.listDoctors(search || undefined),
    placeholderData: (prev) => prev,
  });

  const statusMutation = useMutation({
    mutationFn: ({ userId, isActive }: { userId: number; isActive: boolean }) =>
      adminService.setDoctorStatus(userId, isActive),
    onSuccess: (_, { isActive }) => {
      toast.success(isActive ? "Doctor account activated." : "Doctor account deactivated.");
      qc.invalidateQueries({ queryKey: ["adminDoctors"] });
      qc.invalidateQueries({ queryKey: ["adminDashboard"] });
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Failed to update status.";
      toast.error(msg);
    },
  });

  const filtered = doctors ?? [];

  return (
    <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Manage Doctors</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              View, edit, and control access for all doctor accounts.
            </p>
          </div>
          <Button asChild className="gap-2">
            <Link to="/admin-dashboard/doctors/add">
              <UserPlus className="h-4 w-4" />
              Add Doctor
            </Link>
          </Button>
        </div>

        {/* Search */}
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by name or email…"
            className="h-10 rounded-xl pl-9"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {/* Error */}
        {isError && (
          <div className="flex items-center gap-3 rounded-2xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            Failed to load doctors.
            <button
              onClick={() => refetch()}
              className="ml-auto flex items-center gap-1 hover:underline"
            >
              <RefreshCw className="h-3.5 w-3.5" /> Retry
            </button>
          </div>
        )}

        {/* Table */}
        <div className="overflow-hidden rounded-2xl border border-border bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-surface text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  <th className="px-4 py-3 text-left">Name</th>
                  <th className="px-4 py-3 text-left">Email</th>
                  <th className="px-4 py-3 text-left">Mobile</th>
                  <th className="px-4 py-3 text-left">Specialization</th>
                  <th className="px-4 py-3 text-left">Hospital</th>
                  <th className="px-4 py-3 text-left">Status</th>
                  <th className="px-4 py-3 text-left">Created</th>
                  <th className="px-4 py-3 text-left">Actions</th>
                </tr>
              </thead>
              <tbody>
                {isLoading &&
                  [0, 1, 2, 3].map((i) => (
                    <tr key={i} className="border-b border-border">
                      {[...Array(8)].map((_, j) => (
                        <td key={j} className="px-4 py-3">
                          <div className="h-4 w-full animate-pulse rounded bg-surface" />
                        </td>
                      ))}
                    </tr>
                  ))}

                {!isLoading && filtered.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center text-muted-foreground">
                      No doctors found.{" "}
                      <Link
                        to="/admin-dashboard/doctors/add"
                        className="text-primary hover:underline"
                      >
                        Add the first one →
                      </Link>
                    </td>
                  </tr>
                )}

                {filtered.map((doc) => (
                  <motion.tr
                    key={doc.user_id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="border-b border-border last:border-0 hover:bg-surface/50"
                  >
                    <td className="px-4 py-3 font-medium text-foreground">{doc.full_name}</td>
                    <td className="px-4 py-3 text-muted-foreground">{doc.email}</td>
                    <td className="px-4 py-3 text-muted-foreground">{doc.mobile_number ?? "—"}</td>
                    <td className="px-4 py-3 text-muted-foreground">{doc.specialization ?? "—"}</td>
                    <td className="px-4 py-3 text-muted-foreground">{doc.hospital ?? "—"}</td>
                    <td className="px-4 py-3">
                      <Badge
                        variant="outline"
                        className={cn(
                          "text-[10px] font-semibold",
                          doc.is_active
                            ? "border-green-200 bg-green-50 text-green-700"
                            : "border-red-200 bg-red-50 text-red-700",
                        )}
                      >
                        {doc.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <Link
                          to="/admin-dashboard/doctors/$userId"
                          params={{ userId: String(doc.user_id) }}
                          title="View Details"
                          className="inline-flex items-center justify-center rounded-lg p-1.5 text-muted-foreground transition hover:bg-surface hover:text-primary"
                        >
                          <Eye className="h-4 w-4" />
                        </Link>
                        <Link
                          to="/admin-dashboard/doctors/$userId/edit"
                          params={{ userId: String(doc.user_id) }}
                          title="Edit"
                          className="inline-flex items-center justify-center rounded-lg p-1.5 text-muted-foreground transition hover:bg-surface hover:text-primary"
                        >
                          <Pencil className="h-4 w-4" />
                        </Link>
                        {doc.is_active ? (
                          <button
                            title="Deactivate"
                            disabled={statusMutation.isPending}
                            onClick={() =>
                              statusMutation.mutate({ userId: doc.user_id, isActive: false })
                            }
                            className="rounded-lg p-1.5 text-muted-foreground transition hover:bg-red-50 hover:text-red-600 disabled:opacity-40"
                          >
                            <XCircle className="h-4 w-4" />
                          </button>
                        ) : (
                          <button
                            title="Activate"
                            disabled={statusMutation.isPending}
                            onClick={() =>
                              statusMutation.mutate({ userId: doc.user_id, isActive: true })
                            }
                            className="rounded-lg p-1.5 text-muted-foreground transition hover:bg-green-50 hover:text-green-600 disabled:opacity-40"
                          >
                            <CheckCircle className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
  );
}
