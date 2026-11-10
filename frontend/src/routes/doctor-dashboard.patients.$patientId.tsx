import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  Clock,
  User,
  Heart,
  Stethoscope,
  Users2,
  Gift,
  FileCheck,
  ShieldAlert,
  Loader2,
  Phone,
  Mail,
  MapPin,
  CheckCheck,
  XCircle,
  Sparkles,
  Bot,
} from "lucide-react";
import { DoctorPageShell } from "@/components/doctor-page-shell";
import { MotionCard } from "@/components/motion-card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { doctorService } from "@/lib/api";
import { ACP_SECTIONS, getSectionStatus, type AcpSectionKey } from "@/lib/acp-workflow";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/doctor-dashboard/patients/$patientId")({
  component: PatientAcpDetailsPage,
});

function PatientAcpDetailsPage() {
  const { patientId } = Route.useParams();
  const numericPatientId = Number(patientId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["doctorPatientDetails", numericPatientId],
    queryFn: () => doctorService.getPatientDetails(numericPatientId),
    enabled: !isNaN(numericPatientId) && numericPatientId > 0,
    retry: 1,
  });

  const {
    data: aiData,
    isLoading: isAiLoading,
  } = useQuery({
    queryKey: ["aiDoctorDashboard", numericPatientId],
    queryFn: () => doctorService.getAiDashboard(numericPatientId),
    enabled: !isNaN(numericPatientId) && numericPatientId > 0,
    retry: 1,
  });

  const reviewMutation = useMutation({
    mutationFn: (status: string) =>
      doctorService.reviewPatientACP(numericPatientId, status),
    onSuccess: (_, status) => {
      toast.success(`ACP clinical status updated to "${status}".`);
      queryClient.invalidateQueries({ queryKey: ["doctorPatientDetails", numericPatientId] });
      queryClient.invalidateQueries({ queryKey: ["doctorPatients"] });
    },
    onError: (err: any) => {
      toast.error(err?.message || "Failed to update review status.");
    },
  });

  if (isLoading) {
    return (
      <DoctorPageShell>
        <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm font-medium text-muted-foreground">
            Loading patient ACP record from secure clinical database…
          </p>
        </div>
      </DoctorPageShell>
    );
  }

  if (isError || !data?.patient) {
    return (
      <DoctorPageShell>
        <div className="mx-auto max-w-2xl py-12 text-center">
          <div className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-danger/10 text-danger">
            <ShieldAlert className="h-6 w-6" />
          </div>
          <h2 className="mt-4 text-xl font-bold text-foreground">
            Unable to Load Patient Record
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            {error instanceof Error
              ? error.message
              : "The requested patient record could not be found or you do not have permission to access it."}
          </p>
          <div className="mt-6 flex justify-center gap-3">
            <Button variant="outline" onClick={() => navigate({ to: "/doctor-dashboard" })}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Return to Dashboard
            </Button>
            <Button onClick={() => refetch()}>Retry</Button>
          </div>
        </div>
      </DoctorPageShell>
    );
  }

  const patient = data.patient;
  const acp = data.acp_preferences;
  const dhrs = (data.dhrs || []).filter((dhr: any) => !(dhr.preference_order > 1 && acp?.alternate_dhr_appointed === false));
  const progress = data.progress;

  // Calculate completion percentage based on real DB status
  const sectionStatuses: Record<AcpSectionKey, string> = {
    personal: getSectionStatus("personal", patient, acp, dhrs),
    medical: getSectionStatus("medical", patient, acp, dhrs),
    "end-of-life": getSectionStatus("end-of-life", patient, acp, dhrs),
    proxy: getSectionStatus("proxy", patient, acp, dhrs),
    donation: getSectionStatus("donation", patient, acp, dhrs),
    review: getSectionStatus("review", patient, acp, dhrs),
  };

  const completedCount = Object.values(sectionStatuses).filter((s) => s === "completed").length;
  const completionPercentage = typeof progress?.completion_percentage === "number"
    ? progress.completion_percentage
    : (acp?.is_completed
      ? 100
      : Math.round((completedCount / ACP_SECTIONS.length) * 100));

  const status: string = progress?.status || (
    acp?.review_status === "Reviewed"
      ? "Reviewed"
      : (acp?.is_completed || acp?.completed_at
        ? "Pending Review"
        : (completionPercentage === 100
          ? "Completed – Not Submitted"
          : (completionPercentage === 0 ? "Not Started" : "In Progress")))
  );

  const statusBadgeStyle = (st: string) => {
    switch (st) {
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
  };

  const lastUpdatedRaw = acp?.updated_at || patient?.updated_at || patient?.created_at;
  const lastUpdatedFormatted = lastUpdatedRaw
    ? new Date(lastUpdatedRaw).toLocaleString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "Not recorded";

  return (
    <DoctorPageShell>
      <div className="mx-auto max-w-5xl space-y-6 pb-12">
        {/* Top navigation breadcrumb */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate({ to: "/doctor-dashboard" })}
            className="rounded-xl hover:bg-surface"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Patients
          </Button>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Clinical View</span>
            <Badge variant="outline" className="border-border bg-white text-xs">
              Patient ID: #{patient.patient_id}
            </Badge>
          </div>
        </div>

        {/* Header Hero Card */}
        <MotionCard className="overflow-hidden p-6 sm:p-8">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
            <div className="flex items-start gap-4">
              <div className="grid h-16 w-16 shrink-0 place-items-center rounded-2xl bg-brand-gradient text-2xl font-bold text-white shadow-md">
                {patient.full_name?.charAt(0).toUpperCase() || "P"}
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2.5">
                  <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
                    {patient.full_name}
                  </h1>
                  <Badge
                    className={cn(
                      "rounded-full border px-2.5 py-0.5 text-xs font-semibold",
                      statusBadgeStyle(status)
                    )}
                  >
                    {status}
                  </Badge>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">
                  {patient.email || "No email on file"} · Registered:{" "}
                  {new Date(patient.created_at).toLocaleDateString()}
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
                  <span className="inline-flex items-center gap-1">
                    <Clock className="h-3.5 w-3.5" /> Last Updated: {lastUpdatedFormatted}
                  </span>
                  {patient.preferred_language && (
                    <span>Language: <strong>{patient.preferred_language}</strong></span>
                  )}
                </div>
              </div>
            </div>

            {/* Doctor Review Actions */}
            <div className="flex flex-col items-start gap-2 sm:flex-row sm:items-center lg:flex-col lg:items-end">
              {status === "Pending Review" && (
                <Button
                  onClick={() => reviewMutation.mutate("Reviewed")}
                  disabled={reviewMutation.isPending}
                  className="rounded-xl bg-emerald-600 text-white shadow-sm hover:bg-emerald-700"
                >
                  {reviewMutation.isPending ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <CheckCheck className="mr-2 h-4 w-4" />
                  )}
                  Approve & Acknowledge ACP
                </Button>
              )}
              {status === "Reviewed" && (
                <div className="flex items-center gap-2 text-xs font-medium text-emerald-600">
                  <CheckCircle2 className="h-4 w-4" />
                  Clinically Reviewed & Acknowledged
                  <Button
                    variant="outline"
                    size="sm"
                    className="ml-2 h-7 rounded-lg text-xs"
                    onClick={() => reviewMutation.mutate("Pending Review")}
                    disabled={reviewMutation.isPending}
                  >
                    Re-open Review
                  </Button>
                </div>
              )}
              {status !== "Pending Review" && status !== "Reviewed" && (
                <div className="rounded-xl border border-dashed border-border bg-surface/50 px-3 py-1.5 text-xs text-muted-foreground">
                  Draft record ({status}) · Review eligible after patient submission
                </div>
              )}
            </div>
          </div>

          <Separator className="my-6" />

          {/* Progress & Section completion bar */}
          <div>
            <div className="mb-2 flex items-center justify-between text-xs">
              <span className="font-semibold text-foreground">
                Overall ACP Completion: {completionPercentage}%
              </span>
              <span className="text-muted-foreground">
                {completedCount} of {ACP_SECTIONS.length} sections completed
              </span>
            </div>
            <Progress value={completionPercentage} className="h-2 rounded-full" />

            <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
              {ACP_SECTIONS.map((sec) => {
                const st = sectionStatuses[sec.key];
                return (
                  <div
                    key={sec.key}
                    className={cn(
                      "flex items-center gap-2 rounded-lg border p-2 text-xs",
                      st === "completed"
                        ? "border-success/30 bg-success/5 text-success"
                        : st === "in_progress"
                          ? "border-warning/30 bg-warning/5 text-warning"
                          : "border-border bg-surface text-muted-foreground"
                    )}
                  >
                    {st === "completed" ? (
                      <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
                    ) : (
                      <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                    )}
                    <span className="truncate font-medium">{sec.title}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </MotionCard>

        {/* Incomplete Plan Warning Banner */}
        {!acp && (
          <div className="flex items-start gap-3 rounded-2xl border border-warning/30 bg-warning/10 p-5 text-warning">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
            <div>
              <h4 className="font-bold text-foreground">No Advance Care Plan Submitted Yet</h4>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Patient <strong>{patient.full_name}</strong> has registered their account, but has not
                yet recorded Advance Care Planning directives. Incomplete sections below reflect missing
                patient inputs without placeholder defaults.
              </p>
            </div>
          </div>
        )}

        {/* SECTION 1: Personal Information */}
        <SectionCard
          title="1. Personal & Clinical Information"
          icon={User}
          status={sectionStatuses.personal}
        >
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <InfoItem label="Full Name" value={patient.full_name} />
            <InfoItem label="Age" value={patient.age ? `${patient.age} years` : undefined} />
            <InfoItem label="Gender" value={patient.gender} />
            <InfoItem
              label="Date of Birth"
              value={patient.date_of_birth ? new Date(patient.date_of_birth).toLocaleDateString() : undefined}
            />
            <InfoItem label="Phone Number" value={patient.phone} icon={Phone} />
            <InfoItem label="Email Address" value={patient.email} icon={Mail} />
            <InfoItem label="Preferred Language" value={patient.preferred_language} />
            <InfoItem
              label="Government ID"
              value={
                patient.government_id_type && patient.government_id_number
                  ? `${patient.government_id_type}: ${patient.government_id_number}`
                  : patient.government_id_number || patient.government_id_type
              }
            />
            <InfoItem label="Panchayat / Municipality" value={patient.municipality_panchayat} />
          </div>

          <div className="mt-4 space-y-3">
            <InfoBlock
              label="Residential Address"
              value={patient.address || patient.permanent_address || patient.current_address}
              icon={MapPin}
            />
            <div className="grid gap-3 sm:grid-cols-2">
              <InfoBlock label="Permanent Address" value={patient.permanent_address} placeholder="Not provided." />
              <InfoBlock label="Current Address" value={patient.current_address || patient.address} placeholder="Not provided." />
            </div>
            <InfoBlock
              label="Personal Values, Beliefs & Goals"
              value={patient.personal_values || (patient.beliefs_values?.includes("[") ? undefined : patient.beliefs_values)}
              placeholder="No personal beliefs or spiritual values specified by patient."
            />
          </div>
          <div className="mt-5 rounded-xl border border-border bg-surface p-4">
            <h3 className="text-sm font-semibold text-foreground">Medical History & Allergies</h3>
            <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
              <InfoBlock label="Chronic Medical Conditions" value={patient.chronic_conditions} placeholder="Not recorded." />
              <InfoBlock label="Major Illness / Hospitalization" value={patient.serious_hospitalization} placeholder="Not recorded." />
              <InfoBlock label="Long-term Medications" value={patient.long_term_medications} placeholder="Not recorded." />
              <InfoBlock label="Known Allergies" value={patient.allergies} placeholder="Not recorded." />
            </div>
          </div>
        </SectionCard>

        {/* SECTION 2: Medical Treatment Preferences */}
        <SectionCard
          title="2. Medical Treatment Preferences (Life-Sustaining Directives)"
          icon={Stethoscope}
          status={sectionStatuses.medical}
        >
          {!acp ? (
            <IncompleteNotice message="Patient has not specified medical treatment preferences." />
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <TreatmentCard
                title="Cardiopulmonary Resuscitation (CPR)"
                pref={acp.cpr_preference}
              />
              <TreatmentCard
                title="Mechanical Ventilation"
                pref={acp.ventilator_preference}
              />
              <TreatmentCard
                title="Renal Dialysis"
                pref={acp.dialysis_preference}
              />
              <TreatmentCard
                title="Chemotherapy"
                pref={acp.chemotherapy_preference}
              />
              <TreatmentCard
                title="Radiotherapy"
                pref={acp.radiotherapy_preference}
              />
              <TreatmentCard
                title="Major Surgery"
                pref={acp.surgery_preference}
              />
              <TreatmentCard
                title="Artificial Hydration (IV / Tube Fluids)"
                pref={acp.iv_fluids_preference}
              />
              <TreatmentCard
                title="Artificial Nutrition / Feeding Tube"
                pref={acp.nutrition_hydration_preference}
              />
            </div>
          )}
        </SectionCard>

        {/* SECTION 3: End-of-Life & Comfort Care */}
        <SectionCard
          title="3. End-of-Life & Comfort Care Preferences"
          icon={Heart}
          status={sectionStatuses["end-of-life"]}
        >
          {!acp ? (
            <IncompleteNotice message="Patient has not recorded end-of-life or palliative care preferences." />
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <InfoItem
                  label="Preferred Place of Care"
                  value={acp.preferred_place_of_care}
                  highlight
                />
                <InfoItem label="Goals of Care" value={acp.goals_of_care} />
                <InfoItem
                  label="Preferred Hospital / Facility"
                  value={acp.preferred_hospital}
                />
                <InfoItem
                  label="Preferred Attending Physician"
                  value={
                    acp.preferred_physician_name
                      ? `${acp.preferred_physician_name}${
                          acp.preferred_physician_designation
                            ? ` (${acp.preferred_physician_designation})`
                            : ""
                        }`
                      : undefined
                  }
                />
              </div>

              <InfoBlock
                label="Pain Management & Comfort Care Wishes"
                value={acp.pain_management}
                placeholder="No specific pain relief instructions recorded."
              />

              <InfoBlock
                label="Special Focus & Priorities at End-of-Life"
                value={acp.special_focus_priority}
                placeholder="No special focus instructions recorded."
              />

              <InfoBlock
                label="Additional End-of-Life Wishes"
                value={acp.additional_wishes}
                placeholder="No additional wishes specified."
              />
            </div>
          )}
        </SectionCard>

        {/* SECTION 4: Designated Healthcare Representatives (DHR / Proxy) */}
        <SectionCard
          title="4. Designated Healthcare Representative(s) (Proxy / DHR)"
          icon={Users2}
          status={sectionStatuses.proxy}
        >
          {dhrs.length === 0 ? (
            <IncompleteNotice message="No Designated Healthcare Representatives (DHR) have been appointed by this patient." />
          ) : (
            <>
            {acp?.alternate_dhr_appointed !== null && acp?.alternate_dhr_appointed !== undefined && (
              <p className="mb-3 text-xs text-muted-foreground">Alternate representative appointed: <strong>{acp.alternate_dhr_appointed ? "Yes" : "No"}</strong></p>
            )}
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {dhrs.map((dhr: any, idx: number) => (
                <div
                  key={dhr.id || idx}
                  className="rounded-xl border border-border bg-surface p-4 shadow-sm"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-base font-bold text-foreground">
                          {dhr.full_name}
                        </span>
                        <Badge variant="outline" className="text-[10px]">
                          Rank #{dhr.preference_order || idx + 1}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Relationship: <strong>{dhr.relationship || "Not specified"}</strong>
                      </p>
                    </div>
                  </div>

                  <Separator className="my-3" />

                  <div className="grid grid-cols-1 gap-2 text-xs sm:grid-cols-2">
                    <div>
                      <span className="text-muted-foreground">Primary Mobile:</span>
                      <p className="font-medium text-foreground">{!dhr.mobile_primary || ["pending", "not specified"].includes(String(dhr.mobile_primary).toLowerCase().trim()) ? "Not provided" : dhr.mobile_primary}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Email:</span>
                      <p className="font-medium text-foreground truncate">{!dhr.email_primary || ["pending@example.com", "not_specified@example.com"].includes(String(dhr.email_primary).toLowerCase().trim()) ? "Not provided" : dhr.email_primary}</p>
                    </div>
                    {dhr.permanent_address && (
                      <div className="sm:col-span-2">
                        <span className="text-muted-foreground">Address:</span>
                        <p className="font-medium text-foreground">{dhr.permanent_address}</p>
                      </div>
                    )}
                    {(dhr.government_id_type || dhr.government_id_number) && (
                      <div className="sm:col-span-2">
                        <span className="text-muted-foreground">Government ID (optional):</span>
                        <p className="font-medium text-foreground">{[dhr.government_id_type, dhr.government_id_number].filter(Boolean).join(": ")}</p>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
            </>
          )}
        </SectionCard>

        {/* SECTION 5: Organ & Body Donation */}
        <SectionCard
          title="5. Organ & Body Donation Directives"
          icon={Gift}
          status={sectionStatuses.donation}
        >
          {!acp ? (
            <IncompleteNotice message="Patient has not recorded organ or tissue donation preferences." />
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="rounded-xl border border-border bg-surface p-4">
                  <span className="text-xs font-medium text-muted-foreground">
                    Organ Donation Choice
                  </span>
                  <div className="mt-2 flex items-center gap-2">
                    <ChoiceBadge value={acp.organ_donation} />
                    <span className="text-sm font-semibold text-foreground">
                      {formatChoice(acp.organ_donation)}
                    </span>
                  </div>
                </div>
                <div className="rounded-xl border border-border bg-surface p-4">
                  <span className="text-xs font-medium text-muted-foreground">
                    Anatomical Body Donation
                  </span>
                  <div className="mt-2 flex items-center gap-2">
                    <ChoiceBadge value={acp.body_donation} />
                    <span className="text-sm font-semibold text-foreground">
                      {formatChoice(acp.body_donation)}
                    </span>
                  </div>
                </div>
              </div>

              <InfoBlock
                label="Last Rites & Funeral Preferences"
                value={acp.last_rites}
                placeholder="No specific last rites or funeral instructions specified."
              />
            </div>
          )}
        </SectionCard>

        {/* SECTION 6: Plan Confirmation & Governance */}
        <SectionCard
          title="6. Confirmation, Verification & Legal Governance"
          icon={FileCheck}
          status={sectionStatuses.review}
        >
          {!acp ? (
            <IncompleteNotice message="Advance care planning has not been submitted or finalized." />
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <InfoItem
                  label="Patient Confirmation"
                  value={acp.is_completed ? "Confirmed by Patient" : "Incomplete / Draft"}
                  highlight={acp.is_completed}
                />
                <InfoItem
                  label="Confirmed At"
                  value={
                    acp.completed_at
                      ? new Date(acp.completed_at).toLocaleString()
                      : "Not completed"
                  }
                />
                <InfoItem label="Clinical Review Status" value={acp.review_status} highlight />
                <InfoItem
                  label="Reviewed By Doctor ID"
                  value={acp.reviewed_by_doctor ? `#${acp.reviewed_by_doctor}` : "Not yet reviewed"}
                />
              </div>

              <div className="rounded-xl border border-border bg-surface p-4">
                <h5 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Document Forwarding Authorizations
                </h5>
                <div className="mt-3 flex flex-wrap gap-4 text-xs">
                  <ForwardingTag label="Designated Representatives (DHRs)" active={acp.forward_to_dhrs} />
                  <ForwardingTag label="Attending Physician" active={acp.forward_to_physician} />
                  <ForwardingTag label="Legal Custodian" active={acp.forward_to_custodian} />
                </div>
              </div>
            </div>
          )}
        </SectionCard>

        {/* SECTION 7: AI Questionnaire Insights & Doctor Dashboard Data */}
        <SectionCard
          title="7. AI Questionnaire Insights (FastAPI Microservice)"
          icon={Sparkles}
          status={aiData?.has_session !== false && aiData?.visualization ? "completed" : "in_progress"}
        >
          {isAiLoading ? (
            <div className="flex items-center justify-center gap-2 py-8 text-xs text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
              <span>Querying AI microservice analytics…</span>
            </div>
          ) : !aiData || aiData.has_session === false ? (
            <div className="flex items-start gap-3 rounded-xl border border-border bg-surface p-4 text-xs text-muted-foreground">
              <Bot className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
              <div>
                <p className="font-semibold text-foreground">No AI Questionnaire Session Found</p>
                <p className="mt-0.5">
                  Patient <strong>{patient.full_name}</strong> has not yet participated in the AI-guided questionnaire. All directives displayed in this profile are recorded directly from the standard clinical workflow.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-5">
              {/* Visualization Summary Cards */}
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div className="flex items-center justify-between rounded-xl border border-success/30 bg-success/5 p-4">
                  <div>
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Accepts (WANT)</span>
                    <div className="mt-1 text-2xl font-bold text-success">{aiData.visualization?.preference_summary?.yes ?? 0}</div>
                  </div>
                  <Badge className="border-success/30 bg-success/15 text-success">Yes / Consented</Badge>
                </div>

                <div className="flex items-center justify-between rounded-xl border border-danger/30 bg-danger/5 p-4">
                  <div>
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Declines (DO NOT WANT)</span>
                    <div className="mt-1 text-2xl font-bold text-danger">{aiData.visualization?.preference_summary?.no ?? 0}</div>
                  </div>
                  <Badge className="border-danger/30 bg-danger/15 text-danger">No / Refused</Badge>
                </div>

                <div className="flex items-center justify-between rounded-xl border border-warning/30 bg-warning/5 p-4">
                  <div>
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Unresolved / Unsure</span>
                    <div className="mt-1 text-2xl font-bold text-warning">{aiData.visualization?.preference_summary?.unsure ?? 0}</div>
                  </div>
                  <Badge className="border-warning/30 bg-warning/15 text-warning">Requires Consultation</Badge>
                </div>
              </div>

              {/* Unresolved Preferences High-Priority Alert */}
              {aiData.visualization?.unresolved_preferences && aiData.visualization.unresolved_preferences.length > 0 && (
                <div className="rounded-xl border border-warning/40 bg-warning/10 p-4">
                  <div className="flex items-start gap-2.5">
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
                    <div>
                      <h4 className="text-xs font-bold uppercase tracking-wider text-warning">
                        Unresolved Preferences Requiring Clinical Consultation
                      </h4>
                      <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
                        During the conversational questionnaire, the patient selected <strong>"Unsure"</strong> for the following life-sustaining treatments. Decisions were left uncommitted pending physician clarification:
                      </p>
                      <div className="mt-2.5 flex flex-wrap gap-2">
                        {aiData.visualization.unresolved_preferences.map((prefKey: string) => (
                          <Badge key={prefKey} variant="outline" className="border-warning/40 bg-warning/20 text-xs font-semibold text-warning">
                            {prefKey.replace(/_/g, " ").toUpperCase()}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Unanswered Preferences */}
              {aiData.visualization?.unanswered_preferences && aiData.visualization.unanswered_preferences.length > 0 && (
                <div className="rounded-xl border border-border bg-surface p-4">
                  <span className="text-xs font-semibold text-muted-foreground">Unanswered Treatment Directives in AI Session:</span>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {aiData.visualization.unanswered_preferences.map((unans: string) => (
                      <Badge key={unans} variant="outline" className="border-border text-xs text-muted-foreground">
                        {unans.replace(/_/g, " ")}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Treatment Directives from AI Questionnaire */}
              {aiData.treatment_preferences && (
                <div>
                  <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Directives Recorded from AI Session
                  </h4>
                  <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
                    {Object.entries(aiData.treatment_preferences).map(([key, val]) => (
                      <div key={key} className="flex items-center justify-between rounded-lg border border-border bg-surface/50 p-3 text-xs">
                        <span className="font-medium text-foreground capitalize">{key.replace(/_/g, " ")}</span>
                        <Badge
                          className={cn(
                            "rounded-full text-[11px] font-semibold",
                            val === "Yes"
                              ? "border-success/30 bg-success/10 text-success"
                              : val === "No"
                                ? "border-danger/30 bg-danger/10 text-danger"
                                : val === "Unsure"
                                  ? "border-warning/30 bg-warning/10 text-warning"
                                  : "border-border bg-card text-muted-foreground"
                          )}
                        >
                          {val ? String(val) : "Unanswered"}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Clinical Verification Reminder */}
              <div className="flex items-center gap-2 rounded-lg border border-border/60 bg-surface/30 p-3 text-[11px] text-muted-foreground">
                <ShieldAlert className="h-4 w-4 shrink-0 text-primary" />
                <span>
                  Clinical Governance: AI session outputs inform clinical discussion and do not automatically approve or modify legally binding directives.
                </span>
              </div>
            </div>
          )}
        </SectionCard>
      </div>
    </DoctorPageShell>
  );
}

// ---------------- Helper Components ----------------

function SectionCard({
  title,
  icon: Icon,
  status,
  children,
}: {
  title: string;
  icon: any;
  status: string;
  children: React.ReactNode;
}) {
  return (
    <MotionCard className="overflow-hidden p-5 sm:p-6">
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div className="flex items-center gap-3">
          <div className="grid h-9 w-9 place-items-center rounded-xl bg-primary/10 text-primary">
            <Icon className="h-5 w-5" />
          </div>
          <h3 className="text-base font-bold text-foreground">{title}</h3>
        </div>
        <Badge
          className={cn(
            "rounded-full border px-2.5 py-0.5 text-[11px] font-semibold",
            status === "completed"
              ? "border-success/30 bg-success/10 text-success"
              : status === "in_progress"
                ? "border-warning/30 bg-warning/10 text-warning"
                : "border-border bg-surface text-muted-foreground"
          )}
        >
          {status === "completed"
            ? "Complete"
            : status === "in_progress"
              ? "Partially Complete"
              : "Incomplete"}
        </Badge>
      </div>
      <div className="mt-5">{children}</div>
    </MotionCard>
  );
}

function IncompleteNotice({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-border bg-surface/60 p-4 text-xs text-muted-foreground">
      <AlertTriangle className="h-4 w-4 shrink-0 text-warning" />
      <span>{message}</span>
      <Badge variant="outline" className="ml-auto border-warning/30 text-[10px] text-warning">
        Incomplete
      </Badge>
    </div>
  );
}

function TreatmentCard({ title, pref }: { title: string; pref?: string }) {
  const isWant = pref === "WANT";
  const isDoNotWant = pref === "DO NOT WANT";

  return (
    <div className="flex flex-col justify-between rounded-xl border border-border bg-surface p-3.5">
      <span className="text-xs font-medium text-foreground">{title}</span>
      <div className="mt-3 flex items-center justify-between">
        <Badge
          className={cn(
            "rounded-full border px-2.5 py-0.5 text-[11px] font-semibold",
            isWant
              ? "border-success/30 bg-success/10 text-success"
              : isDoNotWant
                ? "border-danger/30 bg-danger/10 text-danger"
                : "border-border bg-card text-muted-foreground"
          )}
        >
          {isWant ? "WANT" : isDoNotWant ? "DO NOT WANT" : "NOT SPECIFIED"}
        </Badge>
        {isWant && <CheckCircle2 className="h-4 w-4 text-success" />}
        {isDoNotWant && <XCircle className="h-4 w-4 text-danger" />}
      </div>
    </div>
  );
}

function ChoiceBadge({ value }: { value?: string }) {
  const isYes = value?.toUpperCase() === "YES";
  const isNo = value?.toUpperCase() === "NO";
  return (
    <span
      className={cn(
        "grid h-6 w-6 place-items-center rounded-full text-xs font-bold",
        isYes
          ? "bg-success text-white"
          : isNo
            ? "bg-danger text-white"
            : "bg-surface text-muted-foreground"
      )}
    >
      {isYes ? "✓" : isNo ? "✗" : "—"}
    </span>
  );
}

function formatChoice(val?: string) {
  if (!val || val === "NOT SPECIFIED") return "Not specified by patient";
  if (val === "YES") return "Consented / Yes";
  if (val === "NO") return "Declined / No";
  return val;
}

function ForwardingTag({ label, active }: { label: string; active?: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1",
        active
          ? "border-success/30 bg-success/10 text-success"
          : "border-border bg-card text-muted-foreground"
      )}
    >
      {active ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
      {label}: {active ? "Authorized" : "Not authorized"}
    </span>
  );
}

function InfoItem({
  label,
  value,
  icon: Icon,
  highlight = false,
}: {
  label: string;
  value?: string | number | null;
  icon?: any;
  highlight?: boolean;
}) {
  return (
    <div className="rounded-xl border border-border/60 bg-surface/50 p-3">
      <span className="text-[11px] font-medium text-muted-foreground">{label}</span>
      <div className="mt-1 flex items-center gap-1.5">
        {Icon && <Icon className="h-3.5 w-3.5 text-muted-foreground" />}
        <span
          className={cn(
            "text-sm font-semibold truncate",
            value ? (highlight ? "text-primary" : "text-foreground") : "text-muted-foreground/60 italic font-normal"
          )}
        >
          {value !== undefined && value !== null && String(value).trim() !== ""
            ? String(value)
            : "Not provided"}
        </span>
      </div>
    </div>
  );
}

function InfoBlock({
  label,
  value,
  placeholder,
  icon: Icon,
}: {
  label: string;
  value?: string | null;
  placeholder?: string;
  icon?: any;
}) {
  const hasValue = value && value.trim().length > 0;
  return (
    <div className="rounded-xl border border-border/60 bg-surface/50 p-3.5">
      <div className="flex items-center gap-1.5">
        {Icon && <Icon className="h-3.5 w-3.5 text-muted-foreground" />}
        <span className="text-[11px] font-medium text-muted-foreground">{label}</span>
      </div>
      <p
        className={cn(
          "mt-1.5 text-sm leading-relaxed",
          hasValue ? "text-foreground font-medium" : "text-muted-foreground/60 italic"
        )}
      >
        {hasValue ? value : placeholder || "Not provided"}
      </p>
    </div>
  );
}
