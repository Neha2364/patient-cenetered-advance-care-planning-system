import { createFileRoute, Outlet, useRouterState, useNavigate } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import {
  Users,
  ClipboardCheck,
  Loader2,
  Clock,
  Download,
  Search,
  RefreshCw,
  Menu,
  Eye,
  CheckCheck,
  ArrowRight,
  Activity,
  CheckCircle2,
  FileText,
} from "lucide-react";
import { AppSidebar } from "@/components/app-sidebar";
import { MotionCard } from "@/components/motion-card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { authService, doctorService } from "@/lib/api";
import { RequireAuthentication } from "@/components/require-authentication";
import { toast } from "sonner";

export const Route = createFileRoute("/doctor-dashboard")({
  head: () => ({
    meta: [
      { title: "Doctor Dashboard — ACP Care" },
      {
        name: "description",
        content:
          "Monitor patient ACP progress, review submissions, and manage clinical care plans in one place.",
      },
    ],
  }),
  component: DoctorDashboardLayout,
});

function DoctorDashboardLayout() {
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  return pathname === "/doctor-dashboard" ? <DoctorDashboard /> : <Outlet />;
}

function DoctorDashboard() {
  const currentUser = authService.getCurrentUser();
  if (!currentUser) return <RequireAuthentication allowedRoles={["doctor", "admin"]}>{null}</RequireAuthentication>;
  if (currentUser.role !== "doctor" && currentUser.role !== "admin") {
    return <RequireAuthentication allowedRoles={["doctor", "admin"]}>{null}</RequireAuthentication>;
  }

  const doctor = useMemo(() => {
    return {
      name: currentUser?.full_name || "Doctor",
      email: currentUser?.email || "doctor@acpcare.app",
      initial: (currentUser?.full_name || "D").charAt(0).toUpperCase(),
    };
  }, [currentUser]);

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const { data: rawPatients = [], refetch, isLoading } = useQuery({
    queryKey: ["doctorPatients", search, statusFilter],
    queryFn: () => doctorService.getPatients({ 
      search: search || undefined, 
      review_status: statusFilter !== "all" ? statusFilter : undefined
    }),
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
        initial: (p.full_name || "P").charAt(0).toUpperCase(),
        age: p.age ?? "—",
        phone: p.phone || "—",
        email: p.email || "",
        completion: completionPct,
        is_completed: Boolean(p.is_completed),
        status: p.status || p.review_status || "Not Started",
        updated: formattedDate,
        raw_updated: p.last_updated,
        section_progress: p.section_progress || {}
      };
    });
  }, [rawPatients]);

  // Dashboard Statistics derived from unified business rules
  const stats = useMemo(() => {
    const total = patients.length;
    const pendingReviews = patients.filter((p: any) => p.status === "Pending Review").length;
    const reviewed = patients.filter((p: any) => p.status === "Reviewed").length;
    const inProgress = patients.filter((p: any) => p.status === "In Progress" || p.status === "Completed – Not Submitted").length;
    
    return [
      { title: "Total Patients", value: total.toString(), desc: "In clinical registry", icon: Users, tone: "primary" },
      { title: "Pending Review", value: pendingReviews.toString(), desc: "Awaiting clinical acknowledgement", icon: Clock, tone: "warning" },
      { title: "Reviewed ACPs", value: reviewed.toString(), desc: "Clinically acknowledged & approved", icon: ClipboardCheck, tone: "success" },
      { title: "In Progress", value: inProgress.toString(), desc: "Active drafting plans", icon: Loader2, tone: "info" },
    ];
  }, [patients]);

  return (
    <div className="flex min-h-screen w-full bg-surface">
      <AppSidebar role="doctor" user={doctor} />

      <div className="flex min-w-0 flex-1 flex-col">
        <MobileHeader doctor={doctor} />

        <main className="mx-auto w-full max-w-[1600px] flex-1 px-5 py-6 lg:px-8 lg:py-8">
          <Header />

          <section className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {stats.map((s: any, i: number) => (
              <StatCard key={s.title} {...s} delay={i * 0.05} />
            ))}
          </section>

          <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
            <PatientTable 
              patients={patients} 
              search={search} 
              setSearch={setSearch} 
              statusFilter={statusFilter} 
              setStatusFilter={setStatusFilter}
              refetch={refetch}
              isLoading={isLoading}
            />
            <aside className="flex flex-col gap-6">
              <DoctorOverviewPanel patients={patients} refetch={refetch} />
            </aside>
          </div>
        </main>
      </div>
    </div>
  );
}

function MobileHeader({ doctor }: { doctor: any }) {
  return (
    <div className="sticky top-0 z-30 flex items-center justify-between border-b border-border bg-white/80 px-5 py-3 backdrop-blur lg:hidden">
      <Sheet>
        <SheetTrigger asChild>
          <Button variant="ghost" size="icon" className="rounded-xl">
            <Menu className="h-5 w-5" />
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-[260px] p-0">
          <AppSidebar role="doctor" user={doctor} />
        </SheetContent>
      </Sheet>
      <div className="text-sm font-semibold">ACP Care</div>
    </div>
  );
}

function Header() {
  return (
    <header className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-4">
      <div className="min-w-0">
        <h1 className="truncate text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
          Doctor Dashboard
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Monitor patient ACP progress, review submitted directives, and manage clinical care plans.
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <Badge
          variant="outline"
          className="hidden rounded-full border-border bg-white px-3 py-1 text-[11px] font-medium text-primary md:inline-flex"
        >
          <span className="mr-1.5 h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          Clinical Database Connected
        </Badge>
      </div>
    </header>
  );
}

const toneStyles: Record<string, string> = {
  primary: "bg-primary/10 text-primary",
  warning: "bg-amber-500/10 text-amber-600",
  success: "bg-emerald-500/10 text-emerald-600",
  info: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
};

function StatCard({
  title,
  value,
  desc,
  icon: Icon,
  tone,
  delay,
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
        <div className={cn("grid h-11 w-11 shrink-0 place-items-center rounded-xl", toneStyles[tone])}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
      <p className="mt-3 text-xs text-muted-foreground">{desc}</p>
    </motion.div>
  );
}

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

function PatientTable({ patients, search, setSearch, statusFilter, setStatusFilter, refetch, isLoading }: any) {
  const navigate = useNavigate();

  const handleReview = async (patientId: number, status: string) => {
    try {
      await doctorService.reviewPatientACP(patientId, status);
      toast.success(`ACP for Patient #${patientId} acknowledged and marked as Reviewed.`);
      refetch();
    } catch (e: any) {
      toast.error(e?.message || "Failed to update review status.");
    }
  };

  const handleViewPatient = (patientId: number) => {
    navigate({
      to: "/doctor-dashboard/patients/$patientId",
      params: { patientId: String(patientId) },
    });
  };

  return (
    <MotionCard className="p-0">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border p-5">
        <div className="min-w-0">
          <h2 className="text-lg font-bold text-foreground">Patient ACP Records</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {patients.length} patients in clinical registry
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input 
              placeholder="Search by name, email, phone" 
              className="h-10 w-[240px] rounded-xl pl-9 text-xs" 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="h-10 w-[180px] rounded-xl text-xs">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="Pending Review">Pending Review</SelectItem>
              <SelectItem value="Reviewed">Reviewed</SelectItem>
              <SelectItem value="In Progress">In Progress</SelectItem>
              <SelectItem value="Completed – Not Submitted">Completed – Not Submitted</SelectItem>
              <SelectItem value="Not Started">Not Started</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="icon" className="h-10 w-10 rounded-xl" onClick={() => refetch()} title="Refresh list">
            <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin text-primary")} />
          </Button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="border-border hover:bg-transparent">
              <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Patient
              </TableHead>
              <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Age
              </TableHead>
              <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                ACP Completion
              </TableHead>
              <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Status
              </TableHead>
              <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Last Updated
              </TableHead>
              <TableHead className="text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Actions
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {patients.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="h-32 text-center text-sm text-muted-foreground">
                  No patient ACP records found matching the current criteria.
                </TableCell>
              </TableRow>
            ) : (
              patients.map((p: any, i: number) => (
                <motion.tr
                  key={p.id}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.03 * i, duration: 0.25 }}
                  className="border-border transition-colors hover:bg-surface/60"
                >
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <button
                        type="button"
                        onClick={() => handleViewPatient(p.id)}
                        className="grid h-9 w-9 shrink-0 cursor-pointer place-items-center rounded-full bg-brand-gradient text-xs font-semibold text-white transition-opacity hover:opacity-90 shadow-sm"
                        title={`View ${p.name}'s ACP record`}
                      >
                        {p.initial}
                      </button>
                      <div className="min-w-0">
                        <button
                          type="button"
                          onClick={() => handleViewPatient(p.id)}
                          className="truncate text-left text-sm font-semibold text-foreground transition-colors hover:text-primary cursor-pointer block max-w-[190px]"
                          title={`View ${p.name}'s ACP record`}
                        >
                          {p.name}
                        </button>
                        <div className="text-[11px] text-muted-foreground">
                          Patient #{p.id} {p.phone && p.phone !== "—" ? `· ${p.phone}` : ""}
                        </div>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-sm text-foreground">{p.age}</TableCell>
                  <TableCell>
                    <div className="flex w-[160px] items-center gap-2">
                      <Progress 
                        value={p.completion} 
                        className={cn(
                          "h-2 flex-1",
                          p.completion === 100 ? "[&>div]:bg-emerald-500" : "[&>div]:bg-primary"
                        )} 
                      />
                      <span className="text-xs font-semibold text-foreground min-w-[35px] text-right">
                        {p.completion}%
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge className={cn("rounded-full border px-2.5 py-0.5 text-[11px]", statusStyle(p.status))}>
                      {p.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground whitespace-nowrap">{p.updated}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1.5">
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-8 rounded-lg text-xs gap-1 cursor-pointer hover:bg-primary/10 hover:text-primary transition-colors"
                        onClick={() => handleViewPatient(p.id)}
                        title={`View full clinical ACP record for ${p.name}`}
                      >
                        <Eye className="h-3.5 w-3.5" />
                        Inspect
                      </Button>
                      {/* Only allow doctor to review/acknowledge when ACP has been genuinely submitted */}
                      {p.status === "Pending Review" && (
                        <Button 
                          variant="default" 
                          size="sm" 
                          className="h-8 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs gap-1 cursor-pointer transition-colors shadow-sm" 
                          onClick={() => handleReview(p.id, "Reviewed")}
                          title={`Acknowledge and mark ACP as reviewed for ${p.name}`}
                        >
                          <CheckCheck className="h-3.5 w-3.5" />
                          Acknowledge
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </motion.tr>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between border-t border-border px-5 py-3">
        <p className="text-xs text-muted-foreground">
          Showing {patients.length} patient record{patients.length === 1 ? "" : "s"}
        </p>
      </div>
    </MotionCard>
  );
}

/**
 * Replaces the static section completion panel with an active, dynamic Doctor Overview panel.
 * Shows actionable items: Pending reviews, Incomplete plans, and Recently updated records.
 */
function DoctorOverviewPanel({ patients, refetch }: { patients: any[]; refetch: () => void }) {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<"pending" | "in_progress" | "recent">("pending");

  // Filter cohorts based on genuine database statuses
  const pendingReviews = useMemo(() => {
    return patients.filter((p: any) => p.status === "Pending Review");
  }, [patients]);

  const inProgressPlans = useMemo(() => {
    return patients.filter((p: any) => p.status === "In Progress" || p.status === "Completed – Not Submitted");
  }, [patients]);

  const reviewedPlans = useMemo(() => {
    return patients.filter((p: any) => p.status === "Reviewed");
  }, [patients]);

  const recentlyUpdated = useMemo(() => {
    return [...patients]
      .filter((p: any) => p.raw_updated)
      .sort((a: any, b: any) => new Date(b.raw_updated).getTime() - new Date(a.raw_updated).getTime())
      .slice(0, 5);
  }, [patients]);

  const handleReviewPatient = async (patientId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await doctorService.reviewPatientACP(patientId, "Reviewed");
      toast.success(`ACP for Patient #${patientId} acknowledged and reviewed.`);
      refetch();
    } catch (err: any) {
      toast.error(err?.message || "Failed to review ACP.");
    }
  };

  return (
    <MotionCard className="p-0 overflow-hidden">
      <div className="border-b border-border bg-gradient-to-r from-teal-500/10 via-primary/5 to-transparent p-5">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <Activity className="h-4 w-4 text-primary" />
              Doctor Overview
            </h3>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Clinical tasks & action required
            </p>
          </div>
          <Badge variant="outline" className="rounded-full bg-white text-[11px] font-semibold text-primary">
            {pendingReviews.length} Awaiting
          </Badge>
        </div>

        {/* Quick summary metrics */}
        <div className="mt-4 grid grid-cols-3 gap-2">
          <button
            type="button"
            onClick={() => setActiveTab("pending")}
            className={cn(
              "rounded-xl border p-2.5 text-left transition-all cursor-pointer",
              activeTab === "pending"
                ? "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300 shadow-sm"
                : "border-border bg-white/70 hover:bg-white text-muted-foreground"
            )}
          >
            <div className="text-[10px] font-semibold uppercase tracking-wider">Awaiting</div>
            <div className="mt-1 text-lg font-bold text-foreground">{pendingReviews.length}</div>
            <div className="text-[10px] text-muted-foreground">Review</div>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("in_progress")}
            className={cn(
              "rounded-xl border p-2.5 text-left transition-all cursor-pointer",
              activeTab === "in_progress"
                ? "border-blue-500/40 bg-blue-500/10 text-blue-700 dark:text-blue-300 shadow-sm"
                : "border-border bg-white/70 hover:bg-white text-muted-foreground"
            )}
          >
            <div className="text-[10px] font-semibold uppercase tracking-wider">Drafting</div>
            <div className="mt-1 text-lg font-bold text-foreground">{inProgressPlans.length}</div>
            <div className="text-[10px] text-muted-foreground">In Progress</div>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("recent")}
            className={cn(
              "rounded-xl border p-2.5 text-left transition-all cursor-pointer",
              activeTab === "recent"
                ? "border-primary/40 bg-primary/10 text-primary shadow-sm"
                : "border-border bg-white/70 hover:bg-white text-muted-foreground"
            )}
          >
            <div className="text-[10px] font-semibold uppercase tracking-wider">Reviewed</div>
            <div className="mt-1 text-lg font-bold text-foreground">{reviewedPlans.length}</div>
            <div className="text-[10px] text-muted-foreground">Approved</div>
          </button>
        </div>
      </div>

      {/* Dynamic Tab Content */}
      <div className="p-4">
        {activeTab === "pending" && (
          <div>
            <div className="mb-3 flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-foreground">
                Awaiting Doctor Review ({pendingReviews.length})
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-[11px] text-primary p-0 hover:bg-transparent"
                onClick={() => navigate({ to: "/doctor-dashboard/reviews" })}
              >
                Go to Reviews <ArrowRight className="ml-1 h-3 w-3" />
              </Button>
            </div>

            {pendingReviews.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border p-6 text-center">
                <CheckCircle2 className="mx-auto h-8 w-8 text-emerald-500/70" />
                <p className="mt-2 text-xs font-semibold text-foreground">All Submissions Reviewed</p>
                <p className="text-[11px] text-muted-foreground mt-0.5">
                  No completed patient ACP plans are currently awaiting doctor acknowledgement.
                </p>
              </div>
            ) : (
              <div className="space-y-2.5">
                {pendingReviews.map((p: any) => (
                  <div
                    key={p.id}
                    onClick={() => navigate({ to: "/doctor-dashboard/patients/$patientId", params: { patientId: String(p.id) } })}
                    className="group flex items-center justify-between rounded-xl border border-border p-3 transition-colors hover:border-primary/40 hover:bg-surface/80 cursor-pointer"
                  >
                    <div className="min-w-0 pr-2">
                      <p className="truncate text-xs font-bold text-foreground group-hover:text-primary transition-colors">
                        {p.name}
                      </p>
                      <p className="text-[11px] text-muted-foreground">
                        Patient #{p.id} · Age {p.age} · {p.completion}% Complete
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-1.5">
                      <Button
                        size="sm"
                        className="h-7 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] px-2.5 shadow-sm"
                        onClick={(e) => handleReviewPatient(p.id, e)}
                        title="Acknowledge and mark reviewed"
                      >
                        <CheckCheck className="mr-1 h-3 w-3" />
                        Acknowledge
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === "in_progress" && (
          <div>
            <div className="mb-3 flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-foreground">
                In-Progress Patient Plans ({inProgressPlans.length})
              </span>
            </div>

            {inProgressPlans.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border p-6 text-center">
                <p className="text-xs text-muted-foreground">No in-progress plans currently drafting.</p>
              </div>
            ) : (
              <div className="space-y-2.5">
                {inProgressPlans.map((p: any) => (
                  <div
                    key={p.id}
                    onClick={() => navigate({ to: "/doctor-dashboard/patients/$patientId", params: { patientId: String(p.id) } })}
                    className="group flex items-center justify-between rounded-xl border border-border p-3 transition-colors hover:border-primary/40 hover:bg-surface/80 cursor-pointer"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-xs font-bold text-foreground group-hover:text-primary transition-colors">
                        {p.name}
                      </p>
                      <p className="text-[11px] text-muted-foreground mt-0.5">
                        {p.completion}% complete · {p.status}
                      </p>
                    </div>
                    <Button variant="ghost" size="sm" className="h-7 text-xs text-muted-foreground group-hover:text-primary">
                      Inspect <ArrowRight className="ml-1 h-3 w-3" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === "recent" && (
          <div>
            <div className="mb-3 flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-foreground">
                Recently Updated Patients
              </span>
            </div>

            <div className="space-y-2.5">
              {recentlyUpdated.map((p: any) => (
                <div
                  key={p.id}
                  onClick={() => navigate({ to: "/doctor-dashboard/patients/$patientId", params: { patientId: String(p.id) } })}
                  className="group flex items-center justify-between rounded-xl border border-border p-3 transition-colors hover:border-primary/40 hover:bg-surface/80 cursor-pointer"
                >
                  <div className="min-w-0">
                    <p className="truncate text-xs font-bold text-foreground group-hover:text-primary transition-colors">
                      {p.name}
                    </p>
                    <p className="text-[11px] text-muted-foreground flex items-center gap-1 mt-0.5">
                      <Clock className="h-3 w-3" />
                      {p.updated} · {p.completion}% done
                    </p>
                  </div>
                  <Badge variant="outline" className={cn("text-[10px] font-medium rounded-full", statusStyle(p.status))}>
                    {p.status}
                  </Badge>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="border-t border-border bg-surface/50 p-3 text-center">
        <Button
          variant="ghost"
          size="sm"
          className="w-full text-xs font-semibold text-primary hover:bg-primary/10 rounded-xl"
          onClick={() => navigate({ to: "/doctor-dashboard/patients" })}
        >
          View All Patients Registry <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
        </Button>
      </div>
    </MotionCard>
  );
}
