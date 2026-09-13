import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { BarChart3, CheckCircle2, FileText, Users } from "lucide-react";
import { DoctorPageShell } from "@/components/doctor-page-shell";
import { MotionCard } from "@/components/motion-card";
import { doctorService } from "@/lib/api";

export const Route = createFileRoute("/doctor-dashboard/analytics")({ component: AnalyticsPage });

function AnalyticsPage() {
  const { data: patients = [], isLoading } = useQuery({ queryKey: ["doctorPatients", "analytics"], queryFn: () => doctorService.getPatients() });
  const completed = patients.filter((patient: any) => patient.is_completed).length;
  const reviewed = patients.filter((patient: any) => patient.review_status === "Reviewed").length;
  const generated = patients.filter((patient: any) => patient.amd_generated).length;
  const cards = [{ label: "Total Patients", value: patients.length, icon: Users }, { label: "Completed ACPs", value: completed, icon: CheckCircle2 }, { label: "Reviewed ACPs", value: reviewed, icon: BarChart3 }, { label: "AMDs Generated", value: generated, icon: FileText }];
  return <DoctorPageShell><header><h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">Analytics</h1><p className="mt-1 text-sm text-muted-foreground">Live summary of the patient ACP records available to you.</p></header>{isLoading ? <p className="mt-6 text-sm text-muted-foreground">Loading analytics…</p> : <section className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">{cards.map(({ label, value, icon: Icon }) => <MotionCard key={label}><div className="flex items-start justify-between"><div><p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">{label}</p><p className="mt-2 text-3xl font-bold tracking-tight text-foreground">{value}</p></div><div className="grid h-11 w-11 place-items-center rounded-xl bg-primary/10 text-primary"><Icon className="h-5 w-5" /></div></div></MotionCard>)}</section>}</DoctorPageShell>;
}