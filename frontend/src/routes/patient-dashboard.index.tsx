import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { useState, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bell,
  ClipboardList,
  FileText,
  ListChecks,
  ShieldCheck,
  Clock3,
  ChevronRight,
  Sparkles,
  FilePlus2,
  Circle,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Mic,
  Send,
  Menu,
} from "lucide-react";
import { AppSidebar } from "@/components/app-sidebar";
import { MotionCard } from "@/components/motion-card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import { authService, patientService, chatService, aiService } from "@/lib/api";
import {
  ACP_SECTIONS,
  completedSectionKeys,
  nextAcpSection,
  getSectionStatus,
  getSectionProgress,
  getOverallProgress,
  type AcpSectionKey,
} from "@/lib/acp-workflow";

export const Route = createFileRoute("/patient-dashboard/")({
  head: () => ({
    meta: [
      { title: "Patient Dashboard — ACP Care" },
      {
        name: "description",
        content:
          "Track your Advance Care Planning progress, generate documents, and chat with the ACP assistant.",
      },
    ],
  }),
  component: PatientDashboard,
});


function PatientDashboard() {
  const currentUser = authService.getCurrentUser();

  const { data: profile } = useQuery({
    queryKey: ["patientProfile"],
    queryFn: () => patientService.getProfile(),
  });

  const patientId = profile?.patient_id;
  const navigate = useNavigate();

  const { data: acp } = useQuery({
    queryKey: ["patientAcp", patientId],
    queryFn: () => patientService.getACP(patientId!),
    enabled: !!patientId,
  });

  const { data: dhrs = [] } = useQuery({
    queryKey: ["patientDhrs", patientId],
    queryFn: () => patientService.getDHRs(patientId!),
    enabled: !!patientId,
  });

  const { data: auditLogs } = useQuery({
    queryKey: ["patientAuditLogs", patientId],
    queryFn: () => patientService.getAuditLogs(patientId!),
    enabled: !!patientId,
  });

  const patientUser = useMemo(() => {
    const name = profile?.full_name || currentUser?.full_name || "Guest User";
    return {
      name,
      email: profile?.email || currentUser?.email || "guest@acpcare.app",
      initial: name.charAt(0).toUpperCase(),
      greetingName: name.split(" ")[0],
    };
  }, [profile, currentUser]);

  const patientSummary = useMemo(() => {
    const overallProgress = getOverallProgress(profile, acp, dhrs);
    const completedSections = completedSectionKeys(profile, acp, dhrs);
    const isCompleted = Boolean(acp?.is_completed);
    const docsGenerated = acp?.amd_generated ? 1 : 0;
    const sectionsRemaining = ACP_SECTIONS.length - completedSections.length;

    return [
      {
        title: "ACP Completion",
        value: `${overallProgress}%`,
        caption: isCompleted ? "ACP Completed" : (overallProgress > 0 ? "In Progress" : "Start your ACP journey"),
        icon: ClipboardList,
        progress: overallProgress,
      },
      {
        title: "Documents Generated",
        value: `${docsGenerated}`,
        caption: "Complete ACP to generate",
        icon: FileText,
      },
      {
        title: "Sections Remaining",
        value: `${sectionsRemaining}`,
        caption: sectionsRemaining === 0 ? "All done" : "All sections pending",
        icon: ListChecks,
      },
      {
        title: "Doctor Access",
        value: acp?.reviewed_by_doctor ? "Assigned" : "Not Assigned",
        caption: acp?.reviewed_by_doctor ? "Doctor assigned" : "No doctor assigned yet",
        icon: ShieldCheck,
      },
      {
        title: "Last Activity",
        value: auditLogs && auditLogs.length > 0 ? new Date(auditLogs[0].timestamp).toLocaleDateString() : "—",
        caption: auditLogs && auditLogs.length > 0 ? auditLogs[0].action : "No activity yet",
        icon: Clock3,
      },
    ];
  }, [acp, auditLogs, dhrs, profile]);

  const patientTimeline = useMemo(() => {
    if (!auditLogs) return [];
    return auditLogs.slice(0, 5).map((log: any) => ({
      title: log.action,
      meta: new Date(log.timestamp).toLocaleString(),
      state: "done" as const,
    }));
  }, [auditLogs]);

  return (
    <>
      <PageHeader patientUser={patientUser} />

      <section className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {patientSummary.map((s, i) => (
          <SummaryCard key={s.title} {...s} delay={i * 0.04} />
        ))}
      </section>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="flex flex-col gap-6">
          <ProgressTracker profile={profile} acp={acp} dhrs={dhrs} onStart={() => navigate({ to: "/patient-dashboard/acp/$section", params: { section: nextAcpSection(profile, acp, dhrs) } })} onSelect={(section) => navigate({ to: "/patient-dashboard/acp/$section", params: { section } })} />
          <ChatCard patientId={patientId} profile={profile} />
        </div>
        <aside className="flex flex-col gap-6">
          <DocumentsCard acp={acp} onOpen={() => navigate({ to: "/patient-dashboard/documents" })} />
          <TimelineCard patientTimeline={patientTimeline} />
        </aside>
      </div>
    </>
  );
}

function MobileHeader({ patientUser }: { patientUser: any }) {
  return (
    <div className="sticky top-0 z-30 flex items-center justify-between border-b border-border bg-white/80 px-5 py-3 backdrop-blur lg:hidden">
      <Sheet>
        <SheetTrigger asChild>
          <Button variant="ghost" size="icon" className="rounded-xl">
            <Menu className="h-5 w-5" />
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-[260px] p-0">
          <AppSidebar role="patient" user={patientUser} />
        </SheetContent>
      </Sheet>
      <div className="text-sm font-semibold">ACP Care</div>
      <Button variant="ghost" size="icon" className="rounded-xl">
        <Bell className="h-5 w-5" />
      </Button>
    </div>
  );
}

function PageHeader({ patientUser }: { patientUser: any }) {
  return (
    <header className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-4">
      <div className="min-w-0">
        <h1 className="truncate text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
          Welcome, {patientUser.greetingName} <span className="inline-block"></span>
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Start your Advance Care Planning journey whenever you're ready.
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <Badge
          variant="outline"
          className="hidden rounded-full border-border bg-white px-3 py-1 text-[11px] font-medium text-muted-foreground sm:inline-flex"
        >
          No recent updates
        </Badge>
        <Button variant="outline" size="icon" className="hidden rounded-xl lg:inline-flex">
          <Bell className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}

function SummaryCard({
  title,
  value,
  caption,
  icon: Icon,
  progress,
  delay = 0,
}: any) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay, ease: "easeOut" }}
      whileHover={{ y: -3 }}
      className="rounded-2xl border border-border bg-card p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_4px_16px_rgba(15,23,42,0.04)] transition-shadow hover:shadow-[0_10px_30px_-12px_rgba(15,23,42,0.15)]"
    >
      <div className="flex items-start justify-between">
        <div className="min-w-0">
          <div className="truncate text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            {title}
          </div>
          <div className="mt-2 text-3xl font-bold tracking-tight text-foreground">{value}</div>
        </div>
        <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary">
          <Icon className="h-5 w-5" />
        </div>
      </div>
      {progress !== undefined && (
        <div className="mt-3">
          <Progress value={progress} className="h-1.5" />
        </div>
      )}
      <p className="mt-3 line-clamp-2 text-xs text-muted-foreground">{caption}</p>
    </motion.div>
  );
}

function ProgressTracker({
  profile,
  acp,
  dhrs,
  onStart,
  onSelect,
}: {
  profile: any;
  acp: any;
  dhrs: any[];
  onStart: () => void;
  onSelect: (section: AcpSectionKey) => void;
}) {
  const sections = ACP_SECTIONS;
  const completed = new Set(completedSectionKeys(profile, acp, dhrs));

  // Check if any life-sustaining directives remain unresolved
  const hasUnresolvedDecisions = acp && (
    (acp.cpr_preference === "NOT SPECIFIED" && (acp.ventilator_preference !== "NOT SPECIFIED" || acp.dialysis_preference !== "NOT SPECIFIED")) ||
    (acp.ventilator_preference === "NOT SPECIFIED" && (acp.cpr_preference !== "NOT SPECIFIED" || acp.dialysis_preference !== "NOT SPECIFIED")) ||
    (acp.dialysis_preference === "NOT SPECIFIED" && (acp.cpr_preference !== "NOT SPECIFIED" || acp.ventilator_preference !== "NOT SPECIFIED"))
  );

  return (
    <MotionCard className="p-0">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border p-6">
        <div>
          <h2 className="text-lg font-bold text-foreground">ACP Progress Tracker</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            {sections.length} clinical sections • progress reflects your saved ACP choices • Shared with AI chatbot
          </p>
        </div>
        <Button
          onClick={onStart}
          className="h-10 rounded-xl bg-primary px-4 text-sm font-semibold text-primary-foreground hover:bg-primary/90"
        >
          <Sparkles className="mr-2 h-4 w-4" /> {completed.size > 0 ? "Resume ACP" : "Start ACP"}
        </Button>
      </div>

      {hasUnresolvedDecisions && (
        <div className="flex items-center gap-2.5 border-b border-warning/20 bg-warning/5 px-6 py-2.5 text-xs text-warning">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>
            You have life-sustaining treatment decisions marked as unsure or pending. You can revisit them anytime.
          </span>
        </div>
      )}

      <div className="divide-y divide-border">
        {sections.map((section, index) => {
          const status = getSectionStatus(section.key, profile, acp, dhrs);
          const progress = getSectionProgress(section.key, profile, acp, dhrs);

          const badgeConfig = {
            completed: {
              label: "Completed",
              className: "border-success/30 bg-success/10 text-success",
            },
            in_progress: {
              label: "In Progress",
              className: "border-primary/30 bg-primary/10 text-primary",
            },
            pending: {
              label: "Pending",
              className: "border-border bg-surface text-muted-foreground",
            },
          }[status];

          return (
            <motion.button
              key={section.key}
              type="button"
              onClick={() => onSelect(section.key)}
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: 0.05 * index }}
              whileHover={{ backgroundColor: "rgba(15,157,154,0.04)" }}
              className="group flex w-full items-center gap-4 px-6 py-4 text-left transition"
            >
              <div
                className={cn(
                  "grid h-9 w-9 shrink-0 place-items-center rounded-full text-sm font-bold",
                  status === "completed"
                    ? "bg-primary text-primary-foreground"
                    : status === "in_progress"
                      ? "border-2 border-primary text-primary"
                      : "border border-border bg-surface text-muted-foreground"
                )}
              >
                {status === "completed" ? <CheckCircle2 className="h-4 w-4" /> : index + 1}
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="truncate text-sm font-semibold text-foreground">
                    {section.title}
                  </span>
                  <Badge className={cn("rounded-full border px-2 py-0 text-[10px] font-semibold", badgeConfig.className)}>
                    {badgeConfig.label}
                  </Badge>
                </div>
                <div className="mt-2 flex items-center gap-3">
                  <Progress value={progress} className="h-1.5 w-40" />
                  <span className="text-[11px] font-medium text-muted-foreground">{progress}%</span>
                </div>
              </div>
              <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
            </motion.button>
          );
        })}
      </div>
    </MotionCard>
  );
}

function DocumentsCard({ acp, onOpen }: { acp: any; onOpen: () => void }) {
  const canGenerate = Boolean(acp?.is_completed);
  return (
    <MotionCard>
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-sm font-bold text-foreground">ACP Documents</h3>
          <p className="mt-0.5 text-[11px] text-muted-foreground">Living Will & directives</p>
        </div>
        <Button
          size="sm"
          variant="outline"
          disabled={!canGenerate}
          onClick={onOpen}
          className="h-8 rounded-lg border-primary/30 text-xs font-medium text-primary hover:bg-primary/5"
        >
          <FilePlus2 className="mr-1 h-3.5 w-3.5" /> Generate
        </Button>
      </div>
      <div className="mt-5 flex flex-col items-center rounded-2xl border border-dashed border-border bg-surface px-4 py-8 text-center">
        <div className="grid h-14 w-14 place-items-center rounded-2xl bg-primary/10 text-primary">
          <FileText className="h-6 w-6" />
        </div>
        <div className="mt-4 text-sm font-semibold text-foreground">{acp?.amd_generated ? "Documents ready" : "No documents yet"}</div>
        <p className="mt-1 max-w-[220px] text-xs text-muted-foreground">
          {acp?.amd_generated ? "Your AMD has been generated." : "Complete ACP sections to generate your Living Will."}
        </p>
      </div>
    </MotionCard>
  );
}
function TimelineCard({ patientTimeline }: { patientTimeline: any[] }) {
  return (
    <MotionCard>
      <h3 className="text-sm font-bold text-foreground">Activity Timeline</h3>
      <p className="mt-0.5 text-[11px] text-muted-foreground">Recent ACP activity</p>
      {patientTimeline.length === 0 ? (
        <div className="mt-5 flex flex-col items-center rounded-2xl border border-dashed border-border bg-surface px-4 py-8 text-center">
          <div className="grid h-12 w-12 place-items-center rounded-2xl bg-primary/10 text-primary">
            <ClipboardList className="h-5 w-5" />
          </div>
          <div className="mt-3 text-sm font-semibold text-foreground">No activity yet</div>
          <p className="mt-1 max-w-[220px] text-xs text-muted-foreground">
            Your recent ACP actions will appear here.
          </p>
        </div>
      ) : (
        <ol className="mt-5 space-y-4">
          {patientTimeline.map((t, i) => (
            <li key={i} className="relative flex gap-3 pl-1">
              <div className="flex flex-col items-center">
                {t.state === "done" ? (
                  <CheckCircle2 className="h-5 w-5 text-primary" />
                ) : t.state === "active" ? (
                  <div className="grid h-5 w-5 place-items-center">
                    <div className="h-2.5 w-2.5 rounded-full bg-primary ring-4 ring-primary/20" />
                  </div>
                ) : (
                  <Circle className="h-5 w-5 text-muted-foreground/40" />
                )}
                {i < patientTimeline.length - 1 && <div className="mt-1 w-px flex-1 bg-border" />}
              </div>
              <div className="pb-1">
                <div className="text-sm font-medium text-foreground">{t.title}</div>
                <div className="mt-0.5 text-[11px] text-muted-foreground">{t.meta}</div>
              </div>
            </li>
          ))}
        </ol>
      )}
    </MotionCard>
  );
}

function ChatCard({ patientId, profile }: { patientId?: number; profile?: any }) {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);

  const { data: activeSessionResp } = useQuery({
    queryKey: ["activeAiSession", patientId],
    queryFn: aiService.getActiveSession,
    enabled: !!patientId,
  });
  const activeSession = activeSessionResp?.session;

  const { data: history = [] } = useQuery({
    queryKey: ["chatHistory", patientId],
    queryFn: () => chatService.getHistory(patientId!),
    enabled: !!patientId,
  });

  const formattedMessages = useMemo(() => {
    if (!history || history.length === 0) {
      return [
        {
          from: "bot",
          text: activeSession?.question
            ? `Q${activeSession.current_question || 1}: ${activeSession.question}`
            : "Welcome to ACP Care. When you're ready, we'll begin with your personal information to help draft your Advance Care Plan.",
        },
      ];
    }
    return history.flatMap((item: any) => [
      { from: "user", text: item.user_message },
      { from: "bot", text: item.bot_response },
    ]);
  }, [history, activeSession]);

  const handleSendMessage = async (textToSend: string) => {
    const text = textToSend.trim();
    if (!text || !patientId || isSending) return;
    setIsSending(true);
    try {
      let sessionId = activeSession?.session_id;
      if (!sessionId) {
        const lang = profile?.preferred_language?.toLowerCase().includes("kannada") ? "kn" : "en";
        const created = await aiService.createSession(lang);
        sessionId = created.session_id;
      }
      await aiService.sendMessage(sessionId, text);
      setDraft("");
      queryClient.invalidateQueries({ queryKey: ["chatHistory", patientId] });
      queryClient.invalidateQueries({ queryKey: ["activeAiSession", patientId] });
      queryClient.invalidateQueries({ queryKey: ["patientAcp", patientId] });
      queryClient.invalidateQueries({ queryKey: ["patientProfile"] });
      queryClient.invalidateQueries({ queryKey: ["patientDhrs", patientId] });
      queryClient.invalidateQueries({ queryKey: ["patientAuditLogs", patientId] });
      queryClient.invalidateQueries({ queryKey: ["aiDoctorDashboard", patientId] });
    } catch (err: any) {
      console.error(err);
    } finally {
      setIsSending(false);
    }
  };

  const currentQNum = activeSession?.current_question;
  const currentQText = activeSession?.question;
  const currentOptions = activeSession?.options;

  return (
    <MotionCard className="p-0">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border p-5">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-brand-gradient text-white">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <div className="text-sm font-bold text-foreground">ACP Assistant</div>
            <div className="text-[11px] text-muted-foreground">
              {activeSession?.is_completed ? (
                <span className="font-medium text-success">Questionnaire Completed</span>
              ) : currentQNum ? (
                <span>
                  Question {currentQNum} of 20 · <span className="font-medium text-primary">Active</span>
                </span>
              ) : (
                <span>Questionnaire · <span className="text-primary">Ready</span></span>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/patient-dashboard/chat"
            className="flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
          >
            Full Assistant <ChevronRight className="h-3.5 w-3.5" />
          </Link>
          <Badge
            variant="outline"
            className={cn(
              "rounded-full px-2 py-0.5 text-[10px] font-semibold",
              activeSession?.is_completed
                ? "border-success/30 bg-success/10 text-success"
                : "border-primary/25 bg-primary/5 text-primary"
            )}
          >
            {activeSession?.is_completed ? "Completed" : "Ready"}
          </Badge>
        </div>
      </div>

      {/* Active Question Prompt & Choice Pills if session active */}
      {!activeSession?.is_completed && currentQText && (
        <div className="border-b border-primary/15 bg-primary/5 p-4">
          <div className="flex items-start gap-2.5">
            <HelpCircle className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
            <div className="space-y-2">
              <p className="text-xs font-semibold text-foreground">
                Q{currentQNum}: {currentQText}
              </p>
              {currentOptions && currentOptions.length > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-0.5">
                  {currentOptions.map((opt: string) => (
                    <Button
                      key={opt}
                      type="button"
                      size="sm"
                      variant="secondary"
                      onClick={() => handleSendMessage(opt)}
                      disabled={isSending}
                      className="h-7 rounded-lg border border-border bg-white text-[11px] font-medium shadow-2xs hover:border-primary/40 hover:bg-primary/5"
                    >
                      {opt}
                    </Button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="max-h-[320px] space-y-4 overflow-y-auto px-5 py-5">
        {formattedMessages.map((m: any, i: number) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.04 }}
            className={cn("flex", m.from === "user" ? "justify-end" : "justify-start")}
          >
            <div
              className={cn(
                "max-w-[80%] rounded-[20px] px-4 py-3 text-sm leading-relaxed shadow-sm",
                m.from === "user"
                  ? "rounded-br-md bg-primary text-primary-foreground"
                  : "rounded-bl-md bg-surface text-foreground"
              )}
            >
              {m.text || m.message}
            </div>
          </motion.div>
        ))}
        {isSending && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className="inline-block h-2 w-2 animate-ping rounded-full bg-primary" />
            <span>Recording answer in care plan…</span>
          </div>
        )}
      </div>

      <div className="border-t border-border p-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage(draft);
          }}
          className="flex items-center gap-2 rounded-2xl border border-border bg-surface px-3 py-2"
        >
          <button
            type="button"
            className="grid h-9 w-9 place-items-center rounded-xl text-muted-foreground hover:bg-white hover:text-foreground"
            aria-label="Voice input"
          >
            <Mic className="h-4 w-4" />
          </button>
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={
              activeSession?.is_completed
                ? "Questionnaire completed. Click 'Full Assistant' to ask questions…"
                : "Type your answer or click a choice above…"
            }
            disabled={isSending}
            className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={!draft.trim() || isSending}
            className="grid h-9 w-9 place-items-center rounded-full bg-primary text-primary-foreground shadow-sm transition hover:scale-105 hover:bg-primary/90 disabled:opacity-40"
            aria-label="Send"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
        <p className="mt-2 text-center text-[11px] text-muted-foreground">
          Responses update your clinical care plan and progress tracker in real time.
        </p>
      </div>
    </MotionCard>
  );
}

// Keep Link import used
void Link;
