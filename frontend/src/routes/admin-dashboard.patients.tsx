import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Search, AlertTriangle, RefreshCw } from "lucide-react";
import { Input } from "@/components/ui/input";
import { adminService } from "@/lib/api";

export const Route = createFileRoute("/admin-dashboard/patients")({
  head: () => ({ meta: [{ title: "Manage Patients — ACP Care Admin" }] }),
  component: ManagePatientsPage,
});

function ManagePatientsPage() {
  const [search, setSearch] = useState("");

  const { data: patients, isLoading, isError, refetch } = useQuery({
    queryKey: ["adminPatients", search],
    queryFn: () => adminService.listPatients(search || undefined),
    placeholderData: (prev) => prev,
  });

  const list = patients ?? [];

  return (
    <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Manage Patients</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Basic account overview. Clinical records remain protected and are not shown here.
          </p>
        </div>

        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by name or email…"
            className="h-10 rounded-xl pl-9"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {isError && (
          <div className="flex items-center gap-3 rounded-2xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            Failed to load patients.
            <button onClick={() => refetch()} className="ml-auto flex items-center gap-1 hover:underline">
              <RefreshCw className="h-3.5 w-3.5" /> Retry
            </button>
          </div>
        )}

        <div className="overflow-hidden rounded-2xl border border-border bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-surface text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  <th className="px-4 py-3 text-left">Patient Name</th>
                  <th className="px-4 py-3 text-left">Email</th>
                  <th className="px-4 py-3 text-left">Patient ID</th>
                  <th className="px-4 py-3 text-left">Registration Date</th>
                </tr>
              </thead>
              <tbody>
                {isLoading &&
                  [0, 1, 2, 3].map((i) => (
                    <tr key={i} className="border-b border-border">
                      {[...Array(4)].map((_, j) => (
                        <td key={j} className="px-4 py-3">
                          <div className="h-4 w-full animate-pulse rounded bg-surface" />
                        </td>
                      ))}
                    </tr>
                  ))}

                {!isLoading && list.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-4 py-12 text-center text-muted-foreground">
                      No patients found.
                    </td>
                  </tr>
                )}

                {list.map((pat) => (
                  <motion.tr
                    key={pat.user_id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="border-b border-border last:border-0 hover:bg-surface/50"
                  >
                    <td className="px-4 py-3 font-medium text-foreground">{pat.full_name}</td>
                    <td className="px-4 py-3 text-muted-foreground">{pat.email}</td>
                    <td className="px-4 py-3 text-muted-foreground">{pat.patient_id ?? "—"}</td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {new Date(pat.created_at).toLocaleDateString()}
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

