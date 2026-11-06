import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, AlertTriangle } from "lucide-react";
import { AdminShell } from "@/components/admin-shell";
import { Badge } from "@/components/ui/badge";
import { adminService } from "@/lib/api";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/admin-dashboard/doctors/$userId")({
  head: () => ({ meta: [{ title: "Doctor Details — ACP Care Admin" }] }),
  component: DoctorDetailPage,
});

function DoctorDetailPage() {
  const { userId } = Route.useParams();
  const uid = Number(userId);

  const { data: doc, isLoading, isError } = useQuery({
    queryKey: ["adminDoctor", uid],
    queryFn: () => adminService.getDoctor(uid),
  });

  return (
    <AdminShell>
      <div className="mx-auto max-w-lg space-y-6">
        <div className="flex items-center gap-3">
          <Link to="/admin-dashboard/doctors">
            <button className="rounded-xl p-2 text-muted-foreground hover:bg-surface hover:text-foreground">
              <ArrowLeft className="h-4 w-4" />
            </button>
          </Link>
          <h1 className="text-2xl font-bold text-foreground">Doctor Details</h1>
        </div>

        {isLoading && <div className="h-48 animate-pulse rounded-2xl bg-surface" />}

        {isError && (
          <div className="flex items-center gap-3 rounded-2xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            Failed to load doctor details.
          </div>
        )}

        {doc && (
          <div className="rounded-2xl border border-border bg-white p-6 shadow-sm space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <div className="text-xl font-bold text-foreground">{doc.full_name}</div>
                <div className="text-sm text-muted-foreground">{doc.email}</div>
              </div>
              <Badge
                variant="outline"
                className={cn(
                  "text-[10px] font-semibold",
                  doc.is_active
                    ? "border-green-200 bg-green-50 text-green-700"
                    : "border-red-200 bg-red-50 text-red-700"
                )}
              >
                {doc.is_active ? "Active" : "Inactive"}
              </Badge>
            </div>

            <div className="grid grid-cols-2 gap-4 text-sm">
              {[
                ["Mobile", doc.mobile_number ?? "—"],
                ["Specialization", doc.specialization ?? "—"],
                ["Hospital", doc.hospital ?? "—"],
                ["Reg. Number", doc.medical_registration_number ?? "—"],
                ["Created", new Date(doc.created_at).toLocaleDateString()],
                ["User ID", String(doc.user_id)],
              ].map(([label, value]) => (
                <div key={label}>
                  <div className="text-xs font-medium text-muted-foreground">{label}</div>
                  <div className="mt-0.5 text-foreground">{value}</div>
                </div>
              ))}
            </div>

            <div className="pt-2">
              <Link to="/admin-dashboard/doctors/$userId/edit" params={{ userId: String(uid) }}>
                <button className="w-full rounded-xl border border-primary bg-primary/5 py-2 text-sm font-medium text-primary transition hover:bg-primary hover:text-white">
                  Edit Doctor Profile
                </button>
              </Link>
            </div>
          </div>
        )}
      </div>
    </AdminShell>
  );
}

