import { createFileRoute, Outlet, useRouterState, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState, useMemo } from "react";
import { Users, Eye, Search, CheckCircle2, Clock } from "lucide-react";
import { DoctorPageShell } from "@/components/doctor-page-shell";
import { MotionCard } from "@/components/motion-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Input } from "@/components/ui/input";
import { doctorService } from "@/lib/api";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/doctor-dashboard/patients")({
  component: PatientsLayout,
});

function PatientsLayout() {
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  return pathname === "/doctor-dashboard/patients" ? <PatientsPage /> : <Outlet />;
}

function statusStyle(status: string) {
  switch (status) {
    case "Reviewed":
      return "border-emerald-500/25 bg-emerald-500/10 text-emerald-600";
    case "Pending Review":
      return "border-amber-500/25 bg-amber-500/10 text-amber-600";
    case "Completed – Not Submitted":
      return "border-blue-500/25 bg-blue-500/10 text-blue-600";
    case "In Progress":
      return "border-sky-500/25 bg-sky-500/10 text-sky-600";
    case "Not Started":
    default:
      return "border-border bg-surface text-muted-foreground";
  }
}

function PatientsPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");

  const { data: rawPatients = [], isLoading } = useQuery({
    queryKey: ["doctorPatients"],
    queryFn: () => doctorService.getPatients(),
  });

  const patients = useMemo(() => {
    return rawPatients.filter((p: any) => {
      if (!search.trim()) return true;
      const term = search.toLowerCase();
      return (
        p.full_name?.toLowerCase().includes(term) ||
        String(p.patient_id).includes(term) ||
        p.email?.toLowerCase().includes(term) ||
        p.phone?.includes(term)
      );
    });
  }, [rawPatients, search]);

  return (
    <DoctorPageShell>
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
            My Patients
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Complete registry of all patient advance care planning dossiers available to your clinical team.
          </p>
        </div>

        <div className="relative w-full sm:w-[260px]">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by name, ID, or phone"
            className="h-9 w-full rounded-xl pl-9 text-xs"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </header>

      <MotionCard className="mt-6 p-0 overflow-hidden">
        <div className="border-b border-border p-5 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-foreground">Patient ACP Registry</h2>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {patients.length} patient record{patients.length === 1 ? "" : "s"} found
            </p>
          </div>
        </div>

        {isLoading ? (
          <p className="p-8 text-center text-sm text-muted-foreground">Loading patient clinical dossiers…</p>
        ) : patients.length === 0 ? (
          <p className="p-8 text-center text-sm text-muted-foreground">No patient records found matching your query.</p>
        ) : (
          <div className="divide-y divide-border">
            {patients.map((patient: any) => {
              const comp = typeof patient.completion_percentage === "number"
                ? patient.completion_percentage
                : (patient.is_completed ? 100 : 0);

              const status = patient.status || (patient.review_status === "Reviewed" ? "Reviewed" : (patient.is_completed ? "Pending Review" : (comp === 0 ? "Not Started" : "In Progress")));

              let formattedDate = "—";
              if (patient.last_updated) {
                try {
                  formattedDate = new Date(patient.last_updated).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                    year: "numeric"
                  });
                } catch {
                  formattedDate = "—";
                }
              }

              return (
                <div
                  key={patient.patient_id}
                  className="flex flex-wrap items-center justify-between gap-4 p-5 transition-colors hover:bg-surface/50"
                >
                  <div className="flex items-center gap-3 min-w-[260px]">
                    <div className="grid h-11 w-11 place-items-center rounded-2xl bg-brand-gradient text-sm font-bold text-white shadow-sm shrink-0">
                      {patient.full_name?.charAt(0).toUpperCase() || <Users className="h-4 w-4" />}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="font-bold text-foreground text-sm truncate">{patient.full_name}</p>
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Patient #{patient.patient_id} · Age {patient.age ?? "—"} · {patient.preferred_language || "English"}
                      </p>
                      <p className="text-[11px] text-muted-foreground flex items-center gap-1 mt-0.5">
                        <Clock className="h-3 w-3" />
                        Updated {formattedDate}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-6">
                    <div className="hidden sm:block w-[140px]">
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-muted-foreground">ACP Completion</span>
                        <span className="font-bold text-foreground">{comp}%</span>
                      </div>
                      <Progress
                        value={comp}
                        className={cn(
                          "h-2",
                          comp === 100 ? "[&>div]:bg-emerald-500" : "[&>div]:bg-primary"
                        )}
                      />
                    </div>

                    <Badge
                      className={cn(
                        "rounded-full border px-2.5 py-0.5 text-xs font-semibold",
                        statusStyle(status)
                      )}
                    >
                      {status}
                    </Badge>

                    <Button
                      variant="outline"
                      size="sm"
                      className="rounded-xl text-xs gap-1.5 h-9"
                      onClick={() =>
                        navigate({
                          to: "/doctor-dashboard/patients/$patientId",
                          params: { patientId: String(patient.patient_id) },
                        })
                      }
                    >
                      <Eye className="h-3.5 w-3.5" />
                      View Dossier
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </MotionCard>
    </DoctorPageShell>
  );
}
