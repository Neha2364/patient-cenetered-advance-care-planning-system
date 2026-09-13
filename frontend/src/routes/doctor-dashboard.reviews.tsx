import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ClipboardCheck } from "lucide-react";
import { DoctorPageShell } from "@/components/doctor-page-shell";
import { MotionCard } from "@/components/motion-card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { doctorService } from "@/lib/api";
import { toast } from "sonner";

export const Route = createFileRoute("/doctor-dashboard/reviews")({ component: ReviewsPage });

function ReviewsPage() {
  const queryClient = useQueryClient();
  const { data: patients = [], isLoading } = useQuery({ queryKey: ["doctorPatients", "reviews"], queryFn: () => doctorService.getPatients({ review_status: "Pending Review" }) });
  const review = useMutation({ mutationFn: (patientId: number) => doctorService.reviewPatientACP(patientId, "Reviewed"), onSuccess: () => { toast.success("ACP marked as reviewed."); queryClient.invalidateQueries({ queryKey: ["doctorPatients"] }); }, onError: (error: Error) => toast.error(error.message) });
  return <DoctorPageShell><header><h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">ACP Reviews</h1><p className="mt-1 text-sm text-muted-foreground">Review submitted Advance Care Plans awaiting clinical acknowledgement.</p></header><MotionCard className="mt-6 p-0"><div className="border-b border-border p-5"><h2 className="text-lg font-bold">Pending Reviews</h2><p className="mt-0.5 text-xs text-muted-foreground">Only backend records with Pending Review status are shown.</p></div>{isLoading ? <p className="p-6 text-sm text-muted-foreground">Loading reviews…</p> : patients.length === 0 ? <p className="p-6 text-sm text-muted-foreground">No ACP reviews are pending.</p> : <div className="divide-y divide-border">{patients.map((patient: any) => <div key={patient.patient_id} className="flex flex-wrap items-center justify-between gap-4 p-5"><div className="flex items-center gap-3"><div className="grid h-10 w-10 place-items-center rounded-full bg-brand-gradient text-sm font-semibold text-white">{patient.full_name?.charAt(0).toUpperCase() || <ClipboardCheck className="h-4 w-4" />}</div><div><p className="font-semibold text-foreground">{patient.full_name}</p><p className="text-xs text-muted-foreground">Patient #{patient.patient_id} · {patient.email}</p></div></div><div className="flex items-center gap-3"><Badge className="rounded-full border border-warning/25 bg-warning/10 text-warning">{patient.review_status}</Badge><Button disabled={review.isPending} onClick={() => review.mutate(patient.patient_id)} className="rounded-xl">Mark reviewed</Button></div></div>)}</div>}</MotionCard></DoctorPageShell>;
}