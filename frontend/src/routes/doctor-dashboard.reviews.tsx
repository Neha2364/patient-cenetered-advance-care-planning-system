import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, useMemo } from "react";
import {
  ClipboardCheck,
  CheckCircle2,
  Clock,
  Eye,
  CheckCheck,
  Search,
  Users,
  FileText,
  ShieldCheck,
  RefreshCw,
} from "lucide-react";
import { DoctorPageShell } from "@/components/doctor-page-shell";
import { MotionCard } from "@/components/motion-card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { doctorService } from "@/lib/api";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/doctor-dashboard/reviews")({
  component: ReviewsPage,
});

function statusStyle(s: string) {
  switch (s) {
    case "Reviewed":
      return "border-emerald-500/25 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-medium";
    case "Pending Review":
      return "border-amber-500/25 bg-amber-500/10 text-amber-600 dark:text-amber-400 font-semibold";
    case "Completed – Not Submitted":
      return "border-teal-500/25 bg-teal-500/10 text-teal-700 dark:text-teal-300 font-medium";
    case "In Progress":
      return "border-blue-500/25 bg-blue-500/10 text-blue-600 dark:text-blue-400 font-medium";
    case "Not Started":
    default:
      return "border-slate-500/25 bg-slate-500/10 text-slate-600 dark:text-slate-400 font-medium";
  }
}

function ReviewsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [activeTab, setActiveTab] = useState<"pending" | "reviewed" | "all">("pending");

  // Fetch all patients with their real-time calculated ACP progress
  const {
    data: rawPatients = [],
    isLoading,
    isRefetching,
    refetch,
  } = useQuery({
    queryKey: ["doctorPatients"],
    queryFn: () => doctorService.getPatients(),
  });

  const patients = useMemo(() => {
    return rawPatients.map((p: any) => {
      const completionPct = typeof p.completion_percentage === "number"
        ? p.completion_percentage
        : (p.is_completed ? 100 : 0);

      let formattedDate = "—";
      if (p.last_updated) {
        try {
          const d = new Date(p.last_updated);
          formattedDate = d.toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            year: "numeric"
          });
        } catch {
          formattedDate = "—";
        }
      }

      return {
        id: p.patient_id,
        name: p.full_name || `Patient #${p.patient_id}`,
        email: p.email || "",
        phone: p.phone || "—",
        age: p.age ?? "—",
        language: p.preferred_language || "English",
        completion: completionPct,
        is_completed: Boolean(p.is_completed),
        status: p.status || p.review_status || "Not Started",
        last_updated: formattedDate,
        raw_updated: p.last_updated,
        reviewed_by_doctor: p.reviewed_by_doctor,
      };
    });
  }, [rawPatients]);

  // Review mutation
  const reviewMutation = useMutation({
    mutationFn: (patientId: number) => doctorService.reviewPatientACP(patientId, "Reviewed"),
    onSuccess: (_, patientId) => {
      toast.success(`ACP for Patient #${patientId} acknowledged and marked as Reviewed.`);
      // Invalidate both doctorPatients and doctorAnalytics to update all dashboard stats
      queryClient.invalidateQueries({ queryKey: ["doctorPatients"] });
      queryClient.invalidateQueries({ queryKey: ["doctorAnalytics"] });
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to update review status.");
    },
  });

  // Filter cohorts
  // 1. Eligible Pending Reviews: Completed plans awaiting doctor review & acknowledgement
  const eligiblePendingReviews = useMemo(() => {
    return patients.filter((p: any) => {
      const matchesSearch = !search ||
        p.name.toLowerCase().includes(search.toLowerCase()) ||
        String(p.id).includes(search) ||
        p.email.toLowerCase().includes(search.toLowerCase());
      return matchesSearch && p.status === "Pending Review";
    });
  }, [patients, search]);

  // 2. Reviewed ACPs
  const reviewedPatients = useMemo(() => {
    return patients.filter((p: any) => {
      const matchesSearch = !search ||
        p.name.toLowerCase().includes(search.toLowerCase()) ||
        String(p.id).includes(search);
      return matchesSearch && p.status === "Reviewed";
    });
  }, [patients, search]);

  // 3. All Patients
  const allFilteredPatients = useMemo(() => {
    return patients.filter((p: any) => {
      if (!search) return true;
      const s = search.toLowerCase();
      return p.name.toLowerCase().includes(s) || String(p.id).includes(s) || p.email.toLowerCase().includes(s);
    });
  }, [patients, search]);

  return (
    <DoctorPageShell>
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
            ACP Reviews & Acknowledgements
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Clinically inspect and acknowledge submitted patient Advance Care Plans.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="h-9 rounded-xl text-xs gap-1.5"
            onClick={() => refetch()}
          >
            <RefreshCw className={cn("h-3.5 w-3.5", isRefetching && "animate-spin text-primary")} />
            Refresh Reviews
          </Button>
        </div>
      </header>

      {/* Metric Cards Summary */}
      <section className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <MotionCard className="p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Awaiting Clinical Review
              </p>
              <p className="mt-1 text-2xl font-bold text-foreground">
                {eligiblePendingReviews.length}
              </p>
            </div>
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-amber-500/10 text-amber-600">
              <ClipboardCheck className="h-5 w-5" />
            </div>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">Completed plans awaiting doctor sign-off</p>
        </MotionCard>

        <MotionCard className="p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Reviewed & Acknowledged
              </p>
              <p className="mt-1 text-2xl font-bold text-foreground">
                {reviewedPatients.length}
              </p>
            </div>
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-500/10 text-emerald-600">
              <ShieldCheck className="h-5 w-5" />
            </div>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">Verified Advance Care Directives</p>
        </MotionCard>

        <MotionCard className="p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Total Patients in Registry
              </p>
              <p className="mt-1 text-2xl font-bold text-foreground">
                {patients.length}
              </p>
            </div>
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-primary/10 text-primary">
              <Users className="h-5 w-5" />
            </div>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">Under active care management</p>
        </MotionCard>
      </section>

      {/* Main Review Section with Tabs */}
      <MotionCard className="mt-6 p-0 overflow-hidden">
        <div className="border-b border-border p-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <Tabs value={activeTab} onValueChange={(val: any) => setActiveTab(val)}>
              <TabsList className="bg-surface p-1 rounded-xl">
                <TabsTrigger value="pending" className="rounded-lg text-xs font-semibold gap-1.5 data-[state=active]:bg-white data-[state=active]:shadow-sm">
                  <span>Awaiting Review</span>
                  <Badge variant="secondary" className="ml-1 h-5 px-1.5 text-[10px] bg-amber-500/15 text-amber-700">
                    {eligiblePendingReviews.length}
                  </Badge>
                </TabsTrigger>
                <TabsTrigger value="reviewed" className="rounded-lg text-xs font-semibold gap-1.5 data-[state=active]:bg-white data-[state=active]:shadow-sm">
                  <span>Reviewed</span>
                  <Badge variant="secondary" className="ml-1 h-5 px-1.5 text-[10px] bg-emerald-500/15 text-emerald-700">
                    {reviewedPatients.length}
                  </Badge>
                </TabsTrigger>
                <TabsTrigger value="all" className="rounded-lg text-xs font-semibold gap-1.5 data-[state=active]:bg-white data-[state=active]:shadow-sm">
                  <span>All Patients</span>
                  <Badge variant="secondary" className="ml-1 h-5 px-1.5 text-[10px]">
                    {allFilteredPatients.length}
                  </Badge>
                </TabsTrigger>
              </TabsList>
            </Tabs>

            <div className="relative w-full sm:w-[260px]">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search by name, ID, or email"
                className="h-9 w-full rounded-xl pl-9 text-xs"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>
        </div>

        {/* Tab 1: Eligible Pending Reviews */}
        {activeTab === "pending" && (
          <div>
            {isLoading ? (
              <div className="p-12 text-center text-sm text-muted-foreground">
                <RefreshCw className="mx-auto h-6 w-6 animate-spin text-primary mb-2" />
                Loading pending reviews from clinical database…
              </div>
            ) : eligiblePendingReviews.length === 0 ? (
              <div className="p-12 text-center">
                <div className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-emerald-500/10 text-emerald-600 mb-3">
                  <CheckCircle2 className="h-6 w-6" />
                </div>
                <h3 className="text-base font-bold text-foreground">No ACP reviews are currently pending.</h3>
                <p className="mt-1 text-xs text-muted-foreground max-w-md mx-auto">
                  All completed patient Advance Care Planning submissions have been clinically reviewed and acknowledged.
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-4 rounded-xl text-xs"
                  onClick={() => setActiveTab("reviewed")}
                >
                  View Reviewed ACPs
                </Button>
              </div>
            ) : (
              <div className="divide-y divide-border">
                {eligiblePendingReviews.map((patient: any) => (
                  <ReviewItemCard
                    key={patient.id}
                    patient={patient}
                    isReviewPending={reviewMutation.isPending}
                    canReview={true}
                    onReview={() => reviewMutation.mutate(patient.id)}
                    onInspect={() =>
                      navigate({
                        to: "/doctor-dashboard/patients/$patientId",
                        params: { patientId: String(patient.id) },
                      })
                    }
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Reviewed ACPs */}
        {activeTab === "reviewed" && (
          <div>
            {isLoading ? (
              <div className="p-12 text-center text-sm text-muted-foreground">
                <RefreshCw className="mx-auto h-6 w-6 animate-spin text-primary mb-2" />
                Loading reviewed records…
              </div>
            ) : reviewedPatients.length === 0 ? (
              <div className="p-12 text-center">
                <FileText className="mx-auto h-10 w-10 text-muted-foreground/50 mb-2" />
                <h3 className="text-base font-bold text-foreground">No Reviewed ACPs Yet</h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  Once you acknowledge and sign off on completed ACP submissions, they will appear here.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-border">
                {reviewedPatients.map((patient: any) => (
                  <ReviewItemCard
                    key={patient.id}
                    patient={patient}
                    isReviewPending={false}
                    canReview={false}
                    onInspect={() =>
                      navigate({
                        to: "/doctor-dashboard/patients/$patientId",
                        params: { patientId: String(patient.id) },
                      })
                    }
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 3: All Patients */}
        {activeTab === "all" && (
          <div>
            {allFilteredPatients.length === 0 ? (
              <div className="p-12 text-center">
                <p className="text-sm text-muted-foreground">No patient records found.</p>
              </div>
            ) : (
              <div className="divide-y divide-border">
                {allFilteredPatients.map((patient: any) => (
                  <ReviewItemCard
                    key={patient.id}
                    patient={patient}
                    isReviewPending={reviewMutation.isPending}
                    canReview={patient.status === "Pending Review"}
                    onReview={() => reviewMutation.mutate(patient.id)}
                    onInspect={() =>
                      navigate({
                        to: "/doctor-dashboard/patients/$patientId",
                        params: { patientId: String(patient.id) },
                      })
                    }
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </MotionCard>
    </DoctorPageShell>
  );
}

function ReviewItemCard({
  patient,
  isReviewPending,
  canReview = false,
  onReview,
  onInspect,
}: {
  patient: any;
  isReviewPending?: boolean;
  canReview?: boolean;
  onReview?: () => void;
  onInspect: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-4 p-5 transition-colors hover:bg-surface/50">
      <div className="flex items-center gap-4 min-w-[280px]">
        <div className="grid h-12 w-12 place-items-center rounded-2xl bg-brand-gradient text-base font-bold text-white shadow-sm shrink-0">
          {patient.name.charAt(0).toUpperCase()}
        </div>
        <div className="min-w-0">
          <p className="font-bold text-foreground text-sm truncate">{patient.name}</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            Patient #{patient.id} · Age {patient.age} · {patient.language}
          </p>
          <p className="text-[11px] text-muted-foreground flex items-center gap-1 mt-1">
            <Clock className="h-3 w-3" />
            Last updated: {patient.last_updated}
          </p>
        </div>
      </div>

      {/* Completion & Status */}
      <div className="flex items-center gap-6">
        <div className="hidden sm:block w-[140px]">
          <div className="flex justify-between text-xs mb-1">
            <span className="text-muted-foreground">Completion</span>
            <span className="font-bold text-foreground">{patient.completion}%</span>
          </div>
          <Progress
            value={patient.completion}
            className={cn(
              "h-2",
              patient.completion === 100 ? "[&>div]:bg-emerald-500" : "[&>div]:bg-primary"
            )}
          />
        </div>

        <Badge className={cn("rounded-full border px-3 py-1 text-xs", statusStyle(patient.status))}>
          {patient.status}
        </Badge>

        {/* Actions: only allow Review/Acknowledge if eligible */}
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="rounded-xl text-xs gap-1.5 h-9"
            onClick={onInspect}
            title="Inspect patient's clinical ACP dossier"
          >
            <Eye className="h-3.5 w-3.5" />
            Inspect ACP
          </Button>

          {canReview && onReview && (
            <Button
              disabled={isReviewPending}
              onClick={onReview}
              className="rounded-xl text-xs gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm h-9"
              title="Acknowledge and mark ACP as reviewed"
            >
              <CheckCheck className="h-3.5 w-3.5" />
              {isReviewPending ? "Reviewing…" : "Acknowledge"}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
