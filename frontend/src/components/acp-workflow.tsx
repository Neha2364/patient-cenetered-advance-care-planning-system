import { useEffect, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { CheckCircle2, ChevronLeft, ChevronRight, HeartHandshake, Edit3 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { MotionCard } from "@/components/motion-card";
import { aiService, authService, patientService } from "@/lib/api";
import { ACP_SECTIONS, completedSectionKeys, type AcpSectionKey } from "@/lib/acp-workflow";
import { toast } from "sonner";

const isSection = (value: string): value is AcpSectionKey => ACP_SECTIONS.some((section) => section.key === value);
const fieldClass = "mt-1 h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm outline-none focus:ring-2 focus:ring-primary/30";
const labelClass = "text-xs font-medium text-muted-foreground";

const displayValue = (val: any) => {
  if (val === "WANT") return "Yes (I want this treatment)";
  if (val === "DO NOT WANT") return "No (I do not want this treatment)";
  if (val === "UNSURE" || val === "Unsure") return "Unsure / Undecided";
  if (val === "YES") return "Yes";
  if (val === "NO") return "No";
  if (!val || val === "NOT SPECIFIED" || val === "Pending" || val === "Not Specified") return "Not provided";
  return String(val);
};

function EditInChatbotButton({ questionNumber, label = "Edit in Chatbot" }: { questionNumber: number; label?: string }) {
  const navigate = useNavigate();
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      className="flex items-center gap-1.5 text-xs text-primary border-primary/30 hover:bg-primary/10"
      onClick={() => {
        window.sessionStorage.setItem("acpReturnToReview", "1");
        navigate({ to: "/patient-dashboard/chat" as any, search: { editQuestion: questionNumber } as any });
      }}
    >
      <Edit3 className="h-3.5 w-3.5" />
      <span>{label}</span>
    </Button>
  );
}

function ReviewItem({ label, value, badge, fullWidth }: { label: string; value: any; badge?: string; fullWidth?: boolean }) {
  const getBadgeClass = (b?: string) => {
    if (b === "WANT" || b === "YES") return "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-semibold";
    if (b === "DO NOT WANT" || b === "NO") return "bg-rose-500/10 text-rose-600 dark:text-rose-400 font-semibold";
    if (b === "UNSURE") return "bg-amber-500/10 text-amber-600 dark:text-amber-400 font-semibold";
    return "";
  };

  return (
    <div className={`rounded-lg border border-border bg-surface/60 p-3 ${fullWidth ? "sm:col-span-2" : ""}`}>
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <div className="mt-1 flex items-center justify-between gap-2">
        <p className="text-sm font-medium text-foreground">{value || "Not provided"}</p>
        {badge && badge !== "NOT SPECIFIED" && (
          <span className={`text-[11px] px-2 py-0.5 rounded-full ${getBadgeClass(badge)}`}>
            {badge === "WANT" ? "WANT" : badge === "DO NOT WANT" ? "DO NOT WANT" : badge === "UNSURE" ? "UNSURE" : badge}
          </span>
        )}
      </div>
    </div>
  );
}

export function AcpWorkflow({ section }: { section: string }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: profile, isLoading: profileLoading } = useQuery({ queryKey: ["patientProfile"], queryFn: patientService.getProfile });
  const patientId = profile?.patient_id;
  const { data: acp } = useQuery({ queryKey: ["patientAcp", patientId], queryFn: () => patientService.getACP(patientId), enabled: !!patientId, retry: false });
  const { data: dhrs = [] } = useQuery({ queryKey: ["patientDhrs", patientId], queryFn: () => patientService.getDHRs(patientId), enabled: !!patientId });
  const completed = completedSectionKeys(profile, acp, dhrs);
  const activeKey: AcpSectionKey = isSection(section) ? section : "personal";
  const activeIndex = ACP_SECTIONS.findIndex((item) => item.key === activeKey);
  const go = (key: AcpSectionKey) => navigate({ to: "/patient-dashboard/acp/$section", params: { section: key } });
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["patientProfile"] });
    queryClient.invalidateQueries({ queryKey: ["patientAcp", patientId] });
    queryClient.invalidateQueries({ queryKey: ["patientDhrs", patientId] });
  };
  const savedAndContinue = (next: AcpSectionKey) => {
    refresh();
    if (window.sessionStorage.getItem("acpReturnToReview") === "1") {
      const remainingPending = ACP_SECTIONS.filter(
        (s) => s.key !== "review" && s.key !== activeKey && !completed.includes(s.key)
      );
      if (remainingPending.length > 0) {
        const target = remainingPending.some((s) => s.key === next) ? next : remainingPending[0].key;
        go(target);
      } else {
        window.sessionStorage.removeItem("acpReturnToReview");
        go("review");
      }
    } else go(next);
  };

  useEffect(() => {
    if (!profileLoading && !patientId && section !== "profile") {
      navigate({ to: "/patient-dashboard/acp/$section", params: { section: "profile" } });
    }
  }, [navigate, patientId, profileLoading, section]);

  if (profileLoading || (!patientId && section !== "profile")) return <p className="text-sm text-muted-foreground">Preparing your ACP…</p>;
  if (!patientId) return <CreatePatientProfile onCreated={async () => { await queryClient.refetchQueries({ queryKey: ["patientProfile"] }); navigate({ to: "/patient-dashboard/acp/$section", params: { section: "personal" } }); }} />;

  return (
    <div className="max-w-4xl">
      <header>
        <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">Advance Care Planning</h1>
        <p className="mt-1 text-sm text-muted-foreground">Review and finalize your medical preferences recorded via the chatbot. To make updates, click &quot;Edit in Chatbot&quot; on any section.</p>
      </header>

      <MotionCard className="mt-6 p-4">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {ACP_SECTIONS.map((item, index) => (
            <button type="button" key={item.key} onClick={() => go(item.key)} className="text-left">
              <div className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold ${completed.includes(item.key) ? "bg-primary text-primary-foreground" : index === activeIndex ? "border-2 border-primary text-primary" : "bg-surface text-muted-foreground"}`}>
                {completed.includes(item.key) ? <CheckCircle2 className="h-4 w-4" /> : index + 1}
              </div>
              <p className="mt-2 text-xs font-medium text-foreground">{item.title}</p>
            </button>
          ))}
        </div>
      </MotionCard>

      <MotionCard className="mt-6">
        <div className="flex items-center gap-3 border-b border-border pb-4">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-primary/10 text-primary">
            <HeartHandshake className="h-5 w-5" />
          </div>
          <div>
            <h2 className="font-bold">{ACP_SECTIONS[activeIndex].title}</h2>
            <p className="text-xs text-muted-foreground">Step {activeIndex + 1} of {ACP_SECTIONS.length} · Review-Only</p>
          </div>
        </div>

        {activeKey === "personal" && <PersonalReviewCard profile={profile} onNext={() => savedAndContinue("medical")} />}
        {activeKey === "medical" && <MedicalReviewCard acp={acp} profile={profile} onNext={() => savedAndContinue("end-of-life")} />}
        {activeKey === "end-of-life" && <EndOfLifeReviewCard acp={acp} profile={profile} onNext={() => savedAndContinue("proxy")} />}
        {activeKey === "proxy" && <ProxyReviewCard acp={acp} dhrs={dhrs} onNext={() => savedAndContinue("donation")} />}
        {activeKey === "donation" && <DonationReviewCard acp={acp} onNext={() => savedAndContinue("review")} />}
        {activeKey === "review" && (
          <ReviewForm
            patientId={patientId}
            profile={profile}
            acp={acp}
            dhrs={dhrs}
            completed={completed}
            onNavigateSection={go}
            onSaved={() => {
              refresh();
              toast.success("Your ACP has been confirmed and completed!");
              navigate({ to: "/patient-dashboard/documents" });
            }}
          />
        )}

        <div className="mt-6 flex justify-between border-t border-border pt-4">
          <Button variant="outline" disabled={activeIndex === 0} onClick={() => go(ACP_SECTIONS[activeIndex - 1].key)}>
            <ChevronLeft className="mr-1 h-4 w-4" />Back
          </Button>
          <span className="self-center text-xs text-muted-foreground">Answers are collected and updated via the chatbot.</span>
        </div>
      </MotionCard>
    </div>
  );
}

function CreatePatientProfile({ onCreated }: { onCreated: () => void | Promise<void> }) {
  const currentUser = authService.getCurrentUser();
  const [form, setForm] = useState({ phone: "", preferred_language: "English", address: "" });
  const create = useMutation({
    mutationFn: () => {
      if (!currentUser?.user_id) throw new Error("Your account details are unavailable. Please sign in again.");
      return patientService.createProfile({ user_id: currentUser.user_id, ...form });
    },
    onSuccess: onCreated,
    onError: (error: Error) => toast.error(error.message),
  });
  return (
    <div className="max-w-2xl">
      <header>
        <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">Create Patient Profile</h1>
        <p className="mt-1 text-sm text-muted-foreground">A few details are needed before you can begin Advance Care Planning.</p>
      </header>
      <MotionCard className="mt-6">
        <form className="grid gap-4 sm:grid-cols-2" onSubmit={(event) => { event.preventDefault(); create.mutate(); }}>
          <label className={labelClass}>Phone number<input required pattern="[0-9+ ()-]{10,20}" value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} className={fieldClass} /></label>
          <label className={labelClass}>Preferred language<select value={form.preferred_language} onChange={(event) => setForm({ ...form, preferred_language: event.target.value })} className={fieldClass}><option>English</option><option>Kannada</option></select></label>
          <label className={`sm:col-span-2 ${labelClass}`}>Address<textarea required value={form.address} onChange={(event) => setForm({ ...form, address: event.target.value })} className="mt-1 min-h-20 w-full rounded-lg border border-border bg-surface p-3 text-sm outline-none focus:ring-2 focus:ring-primary/30" /></label>
          <div className="sm:col-span-2 mt-2 flex justify-end">
            <Button type="submit" disabled={create.isPending}>{create.isPending ? "Creating…" : "Create profile and continue"}<ChevronRight className="ml-2 h-4 w-4" /></Button>
          </div>
        </form>
      </MotionCard>
    </div>
  );
}

function PersonalReviewCard({ profile, onNext }: { profile: any; onNext: () => void }) {
  const displayName = profile?.full_name || profile?.user?.full_name || "Not provided";
  const displayDob = profile?.date_of_birth ? String(profile.date_of_birth) : (profile?.age ? `Age: ${profile.age}` : "Not provided");
  const displayGender = profile?.gender || "Not provided";

  return (
    <div className="mt-6 space-y-6">
      <div className="flex items-center justify-between border-b border-border pb-3">
        <div>
          <h3 className="text-sm font-semibold text-foreground">Personal Information</h3>
          <p className="text-xs text-muted-foreground">Review your personal and contact details collected by the chatbot.</p>
        </div>
        <EditInChatbotButton questionNumber={1} />
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <ReviewItem label="Full Name" value={displayName} />
        <ReviewItem label="Date of Birth / Age" value={displayDob} />
        <ReviewItem label="Gender" value={displayGender} />
        <ReviewItem label="Mobile Phone Number" value={profile?.phone || "Not provided"} />
        <ReviewItem label="Preferred Language" value={profile?.preferred_language || "English"} />
        <ReviewItem label="Current Residential Address" value={profile?.current_address || profile?.address || "Not provided"} fullWidth />
        <ReviewItem label="Permanent Residential Address" value={profile?.permanent_address || profile?.current_address || profile?.address || "Not provided"} fullWidth />
        <ReviewItem label="Government ID" value={profile?.government_id_type ? `${profile.government_id_type}: ${profile.government_id_number || "Not provided"}` : "Not provided"} />
        <ReviewItem label="Municipality / Panchayat" value={profile?.municipality_panchayat || "Not provided"} />
      </div>

      <div className="flex justify-end pt-4 border-t border-border">
        <Button onClick={onNext} className="flex items-center gap-2">
          <span>Next Section: Medical Preferences</span>
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

function MedicalReviewCard({ acp, profile, onNext }: { acp: any; profile: any; onNext: () => void }) {
  const treatments = [
    { label: "Cardiopulmonary Resuscitation (CPR)", key: "cpr_preference", q: 11 },
    { label: "Mechanical Ventilation", key: "ventilator_preference", q: 12 },
    { label: "Dialysis", key: "dialysis_preference", q: 13 },
    { label: "Artificial Nutrition (Tube Feeding)", key: "nutrition_hydration_preference", q: 18 },
    { label: "Artificial Hydration (IV Fluids)", key: "iv_fluids_preference", q: 17 },
    { label: "Chemotherapy", key: "chemotherapy_preference", q: 14 },
    { label: "Radiotherapy", key: "radiotherapy_preference", q: 15 },
    { label: "Major Surgery / Invasive Operations", key: "surgery_preference", q: 16 },
  ];

  return (
    <div className="mt-6 space-y-6">
      <div className="flex items-center justify-between border-b border-border pb-3">
        <div>
          <h3 className="text-sm font-semibold text-foreground">Medical Treatment Preferences</h3>
          <p className="text-xs text-muted-foreground">Review your medical history and life-sustaining treatment choices.</p>
        </div>
        <EditInChatbotButton questionNumber={7} />
      </div>

      <div>
        <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Medical Background</h4>
        <div className="grid gap-3 sm:grid-cols-2">
          <ReviewItem label="Chronic Medical Conditions" value={profile?.chronic_conditions || "None reported"} />
          <ReviewItem label="Serious Illness / Hospitalization" value={profile?.serious_hospitalization || "None reported"} />
          <ReviewItem label="Current Long-term Medications" value={profile?.long_term_medications || "None reported"} />
          <ReviewItem label="Known Allergies" value={profile?.allergies || "None reported"} />
        </div>
      </div>

      <div>
        <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Life-Sustaining Treatment Directives</h4>
        <div className="grid gap-3 sm:grid-cols-2">
          {treatments.map((t) => (
            <ReviewItem key={t.key} label={t.label} value={displayValue(acp?.[t.key])} badge={acp?.[t.key]} />
          ))}
        </div>
      </div>

      <div className="flex justify-end pt-4 border-t border-border">
        <Button onClick={onNext} className="flex items-center gap-2">
          <span>Next Section: End-of-Life Wishes</span>
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

function EndOfLifeReviewCard({ acp, profile, onNext }: { acp: any; profile: any; onNext: () => void }) {
  return (
    <div className="mt-6 space-y-6">
      <div className="flex items-center justify-between border-b border-border pb-3">
        <div>
          <h3 className="text-sm font-semibold text-foreground">End-of-Life Preferences</h3>
          <p className="text-xs text-muted-foreground">Review your goals of care, preferred place of care, and personal values.</p>
        </div>
        <EditInChatbotButton questionNumber={19} />
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <ReviewItem label="Main Goals of Care" value={acp?.goals_of_care || "Not provided"} />
        <ReviewItem label="Preferred Place of Care" value={acp?.preferred_place_of_care || "Not provided"} />
        <ReviewItem label="Preferred Hospital" value={acp?.preferred_hospital || "No preference"} />
        <ReviewItem label="Preferred Level of Medical Intervention" value={acp?.special_focus_priority || "Not provided"} />
        <ReviewItem label="Preferred Treating Clinician" value={acp?.preferred_physician_name || "Not provided"} />
        <ReviewItem label="Clinician Designation / Institution" value={[acp?.preferred_physician_designation, acp?.preferred_physician_institution].filter(Boolean).join(" · ") || "Not provided"} />
        <ReviewItem label="Important Personal Values & Priorities" value={profile?.personal_values || "Not provided"} fullWidth />
        <ReviewItem label="Additional Wishes or Instructions" value={acp?.additional_wishes || "No additional wishes"} fullWidth />
      </div>

      <div className="flex justify-end pt-4 border-t border-border">
        <Button onClick={onNext} className="flex items-center gap-2">
          <span>Next Section: Healthcare Representative</span>
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

function ProxyReviewCard({ dhrs, acp, onNext }: { dhrs: any[]; acp: any; onNext: () => void }) {
  const primary = dhrs.find((d: any) => d.preference_order === 1) || dhrs[0];
  const alternate = dhrs.find((d: any) => d.preference_order === 2);
  const altAppointed = acp?.alternate_dhr_appointed;

  return (
    <div className="mt-6 space-y-6">
      <div className="flex items-center justify-between border-b border-border pb-3">
        <div>
          <h3 className="text-sm font-semibold text-foreground">Designated Healthcare Representative</h3>
          <p className="text-xs text-muted-foreground">Review the trusted person(s) appointed to make medical decisions on your behalf.</p>
        </div>
        <EditInChatbotButton questionNumber={26} />
      </div>

      <div className="rounded-xl border border-border bg-surface p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-semibold text-primary uppercase tracking-wider">Primary Representative (Preference Rank 1)</h4>
          <span className="text-xs rounded bg-primary/10 text-primary px-2 py-0.5 font-medium">Primary</span>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <ReviewItem label="Full Name" value={primary?.full_name || "Not provided"} />
          <ReviewItem label="Relationship" value={primary?.relationship || "Not provided"} />
          <ReviewItem label="Mobile Phone Number" value={primary?.mobile_primary || "Not provided"} />
          <ReviewItem label="Email Address" value={primary?.email_primary || "Not provided"} />
          <ReviewItem label="Address" value={primary?.permanent_address || "Not provided"} fullWidth />
        </div>
      </div>

      <div className="rounded-xl border border-border bg-surface p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Alternate Representative</h4>
          <span className={`text-xs rounded px-2 py-0.5 font-medium ${altAppointed ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"}`}>
            {altAppointed ? "Appointed" : "Not Appointed"}
          </span>
        </div>
        {altAppointed && alternate ? (
          <div className="grid gap-3 sm:grid-cols-2">
            <ReviewItem label="Full Name" value={alternate?.full_name || "Not provided"} />
            <ReviewItem label="Relationship" value={alternate?.relationship || "Not provided"} />
            <ReviewItem label="Mobile Phone Number" value={alternate?.mobile_primary || "Not provided"} />
            <ReviewItem label="Email Address" value={alternate?.email_primary || "Not provided"} />
            <ReviewItem label="Address" value={alternate?.permanent_address || "Not provided"} fullWidth />
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">
            You chose not to appoint an alternate healthcare representative. Your primary representative will be contacted for all medical decisions.
          </p>
        )}
      </div>

      <div className="flex justify-end pt-4 border-t border-border">
        <Button onClick={onNext} className="flex items-center gap-2">
          <span>Next Section: Organ Donation</span>
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

function DonationReviewCard({ acp, onNext }: { acp: any; onNext: () => void }) {
  return (
    <div className="mt-6 space-y-6">
      <div className="flex items-center justify-between border-b border-border pb-3">
        <div>
          <h3 className="text-sm font-semibold text-foreground">Organ & Body Donation</h3>
          <p className="text-xs text-muted-foreground">Review your donation preferences and funeral/last rites wishes.</p>
        </div>
        <EditInChatbotButton questionNumber={37} />
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <ReviewItem label="Organ Donation" value={displayValue(acp?.organ_donation)} badge={acp?.organ_donation} />
        <ReviewItem label="Body Donation (Medical Education / Research)" value={displayValue(acp?.body_donation)} badge={acp?.body_donation} />
        <ReviewItem label="Last Rites / Funeral Wishes" value={acp?.last_rites || "No specific wishes"} fullWidth />
      </div>

      <div className="flex justify-end pt-4 border-t border-border">
        <Button onClick={onNext} className="flex items-center gap-2">
          <span>Next Section: Confirmation & Review</span>
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

function ReviewForm({ patientId, profile, acp, dhrs, completed, onNavigateSection, onSaved }: any) {
  const [confirmed, setConfirmed] = useState(false);
  const save = useMutation({
    mutationFn: () => aiService.confirmReview(),
    onSuccess: onSaved,
    onError: (e: any) => {
      const message = e?.message || "Failed to confirm ACP.";
      const missingMatch = message.match(/missing:\s*(.+?)(?:\.|$)/i)?.[1];
      if (missingMatch) {
        const fields = missingMatch.split(/,\s*/).filter(Boolean);
        toast.error(message);
        const sectionForField = (field: string): AcpSectionKey => {
          const n = field.toLowerCase();
          if (/representative|dhr|ಪ್ರತಿನಿಧಿ/.test(n)) return "proxy";
          if (/organ|body donation|ಅಂಗದಾನ|ದೇಹದಾನ/.test(n)) return "donation";
          if (/goal|care|wishes|intervention|value|place|ಆರೈಕೆ|ಆಶಯ|ಮೌಲ್ಯ/.test(n)) return "end-of-life";
          if (/medical|treatment|cpr|dialysis|ventilator|nutrition|hydration|chemotherapy|radiotherapy|surgery|condition|allerg|medication|hospital|ಚಿಕಿತ್ಸೆ|ಕಾಯಿಲೆ|ಅಲರ್ಜಿ/.test(n)) return "medical";
          return "personal";
        };
        const missingSections = fields.map(sectionForField);
        const firstIncomplete = ACP_SECTIONS.find((s) => missingSections.includes(s.key))?.key || "personal";
        window.sessionStorage.setItem("acpReturnToReview", "1");
        onNavigateSection(firstIncomplete);
        return;
      }
      toast.error(message);
    },
  });

  const ready = ACP_SECTIONS.slice(0, 5).every((item) => completed.includes(item.key));
  const primary = dhrs.find((d: any) => d.preference_order === 1) || dhrs[0];
  const alternate = dhrs.find((d: any) => d.preference_order === 2);
  const treatments = [
    ["CPR", "cpr_preference"],
    ["Mechanical ventilation", "ventilator_preference"],
    ["Dialysis", "dialysis_preference"],
    ["Artificial nutrition", "nutrition_hydration_preference"],
    ["Artificial hydration", "iv_fluids_preference"],
    ["Chemotherapy", "chemotherapy_preference"],
    ["Radiotherapy", "radiotherapy_preference"],
    ["Major surgery", "surgery_preference"],
  ];

  return (
    <div className="mt-6 space-y-4 text-sm">
      <h3 className="font-semibold text-foreground text-base">Review your complete Advance Care Plan</h3>

      <ReviewGroup title="Personal information" editQ={1}>
        <ReviewLine label="Name" value={profile?.full_name} />
        <ReviewLine label="Date of birth / age" value={profile?.date_of_birth || profile?.age} />
        <ReviewLine label="Gender" value={profile?.gender} />
        <ReviewLine label="Phone" value={profile?.phone} />
        <ReviewLine label="Current address" value={profile?.current_address || profile?.address} />
        <ReviewLine label="Permanent address" value={profile?.permanent_address} />
        <ReviewLine label="Government ID" value={profile?.government_id_type || profile?.government_id_number ? [profile?.government_id_type, profile?.government_id_number].filter(Boolean).join(": ") : null} />
        <ReviewLine label="Municipality / Panchayat" value={profile?.municipality_panchayat} />
        <ReviewLine label="Personal values" value={profile?.personal_values} />
      </ReviewGroup>

      <ReviewGroup title="Medical history" editQ={7}>
        <ReviewLine label="Chronic conditions" value={profile?.chronic_conditions} />
        <ReviewLine label="Serious illness / hospitalization" value={profile?.serious_hospitalization} />
        <ReviewLine label="Medications" value={profile?.long_term_medications} />
        <ReviewLine label="Allergies" value={profile?.allergies} />
      </ReviewGroup>

      <ReviewGroup title="Treatment choices" editQ={11}>
        {treatments.map(([label, key]) => (
          <ReviewLine key={key} label={label} value={displayValue(acp?.[key])} />
        ))}
      </ReviewGroup>

      <ReviewGroup title="Care preferences" editQ={19}>
        <ReviewLine label="Goals of care" value={acp?.goals_of_care} />
        <ReviewLine label="Preferred place" value={acp?.preferred_place_of_care} />
        <ReviewLine label="Preferred hospital" value={acp?.preferred_hospital} />
        <ReviewLine label="Care priority" value={acp?.special_focus_priority} />
        <ReviewLine label="Preferred clinician" value={acp?.preferred_physician_name} />
        <ReviewLine label="Additional wishes" value={acp?.additional_wishes} />
      </ReviewGroup>

      <ReviewGroup title="Healthcare representatives" editQ={26}>
        <ReviewRepresentative title="Primary representative" person={primary} />
        <ReviewLine label="Alternate appointed" value={acp?.alternate_dhr_appointed == null ? "Not recorded" : acp.alternate_dhr_appointed ? "Yes" : "No"} />
        {acp?.alternate_dhr_appointed && <ReviewRepresentative title="Alternate representative" person={alternate} />}
      </ReviewGroup>

      <ReviewGroup title="Donation preferences" editQ={37}>
        <ReviewLine label="Organ donation" value={displayValue(acp?.organ_donation)} />
        <ReviewLine label="Body donation" value={displayValue(acp?.body_donation)} />
        <ReviewLine label="Last rites / funeral wishes" value={acp?.last_rites} />
      </ReviewGroup>

      <label className="flex items-start gap-2 rounded-xl border border-border bg-surface p-4 cursor-pointer">
        <input required type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} className="mt-1 h-4 w-4 text-primary" />
        <span>I have reviewed these saved details and confirm that the recorded choices reflect my current wishes.</span>
      </label>

      {!ready && (
        <div className="rounded-xl border border-warning/30 bg-warning/5 p-3">
          <p className="text-sm text-warning font-medium">Please complete all required sections before confirming your ACP.</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {ACP_SECTIONS.slice(0, 5)
              .filter((item) => !completed.includes(item.key))
              .map((item) => (
                <Button key={item.key} type="button" size="sm" variant="outline" onClick={() => { window.sessionStorage.setItem("acpReturnToReview", "1"); onNavigateSection(item.key); }}>
                  Review {item.title}
                </Button>
              ))}
          </div>
        </div>
      )}

      <div className="flex justify-end">
        <Button disabled={!confirmed || !ready || save.isPending} onClick={() => save.mutate()}>
          {save.isPending ? "Confirming…" : "Confirm and complete ACP"}
        </Button>
      </div>
    </div>
  );
}

function ReviewGroup({ title, editQ, children }: { title: string; editQ?: number; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-border bg-surface p-4">
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-semibold text-foreground">{title}</h4>
        {editQ && <EditInChatbotButton questionNumber={editQ} label="Edit" />}
      </div>
      <div className="grid gap-2 sm:grid-cols-2">{children}</div>
    </section>
  );
}

function ReviewLine({ label, value }: { label: string; value: any }) {
  return (
    <p className="min-w-0">
      <span className="text-muted-foreground">{label}: </span>
      <span className="break-words font-medium text-foreground">{value == null || value === "" ? "Not provided" : String(value)}</span>
    </p>
  );
}

function ReviewRepresentative({ title, person }: { title: string; person: any }) {
  return (
    <div className="sm:col-span-2">
      <h5 className="font-medium text-xs uppercase tracking-wider text-primary mb-1">{title}</h5>
      <div className="grid gap-2 sm:grid-cols-2">
        <ReviewLine label="Name" value={person?.full_name} />
        <ReviewLine label="Relationship" value={person?.relationship} />
        <ReviewLine label="Phone" value={person?.mobile_primary} />
        <ReviewLine label="Email" value={person?.email_primary} />
        <ReviewLine label="Address" value={person?.permanent_address} />
        <ReviewLine label="Government ID" value={person?.government_id_type || person?.government_id_number ? [person?.government_id_type, person?.government_id_number].filter(Boolean).join(": ") : null} />
      </div>
    </div>
  );
}
