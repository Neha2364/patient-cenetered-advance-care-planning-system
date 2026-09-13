import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Users } from "lucide-react";
import { DoctorPageShell } from "@/components/doctor-page-shell";
import { MotionCard } from "@/components/motion-card";
import { Badge } from "@/components/ui/badge";
import { doctorService } from "@/lib/api";

export const Route = createFileRoute("/doctor-dashboard/patients")({ component: PatientsPage });

function PatientsPage() {
  const { data: patients = [], isLoading } = useQuery({ queryKey: ["doctorPatients"], queryFn: () => doctorService.getPatients() });
  return <DoctorPageShell><header><h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">My Patients</h1><p className="mt-1 text-sm text-muted-foreground">Patient ACP records available to your care team.</p></header><MotionCard className="mt-6 p-0"><div className="border-b border-border p-5"><h2 className="text-lg font-bold">Patient ACP Records</h2><p className="mt-0.5 text-xs text-muted-foreground">{patients.length} patients found</p></div>{isLoading ? <p className="p-6 text-sm text-muted-foreground">Loading patients…</p> : patients.length === 0 ? <p className="p-6 text-sm text-muted-foreground">No patient records are available yet.</p> : <div className="divide-y divide-border">{patients.map((patient: any) => <div key={patient.patient_id} className="flex flex-wrap items-center justify-between gap-4 p-5"><div className="flex items-center gap-3"><div className="grid h-10 w-10 place-items-center rounded-full bg-brand-gradient text-sm font-semibold text-white">{patient.full_name?.charAt(0).toUpperCase() || <Users className="h-4 w-4" />}</div><div><p className="font-semibold text-foreground">{patient.full_name}</p><p className="text-xs text-muted-foreground">{patient.email} · Patient #{patient.patient_id}</p></div></div><div className="flex items-center gap-3"><span className="text-sm text-muted-foreground">{patient.preferred_language}</span><Badge className="rounded-full border border-primary/25 bg-primary/10 text-primary">{patient.is_completed ? "ACP complete" : "In progress"}</Badge></div></div>)}</div>}</MotionCard></DoctorPageShell>;
}