import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState, useMemo } from "react";
import {
  Users,
  CheckCircle2,
  Clock,
  ShieldCheck,
  BarChart3,
  PieChart as PieIcon,
  Activity,
  Calendar,
  Filter,
  RefreshCw,
  FileText,
  ArrowUpRight,
  Sparkles,
  ClipboardList,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
  PieChart,
  Pie,
  Legend,
} from "recharts";
import { DoctorPageShell } from "@/components/doctor-page-shell";
import { MotionCard } from "@/components/motion-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { doctorService } from "@/lib/api";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/doctor-dashboard/analytics")({
  component: AnalyticsPage,
});

const TEAL_PRIMARY = "#0d9488";
const TEAL_LIGHT = "#14b8a6";
const AMBER_WARNING = "#f59e0b";
const BLUE_ACCENT = "#3b82f6";
const EMERALD_SUCCESS = "#10b981";
const SLATE_MUTED = "#64748b";

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

function AnalyticsPage() {
  const navigate = useNavigate();
  const [dateFilter, setDateFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

  const {
    data: analytics,
    isLoading,
    isRefetching,
    refetch,
  } = useQuery({
    queryKey: ["doctorAnalytics"],
    queryFn: () => doctorService.getAnalytics(),
  });

  const summary = analytics?.summary || {
    total_patients: 0,
    completed_acps: 0,
    pending_reviews: 0,
    reviewed_acps: 0,
    in_progress_acps: 0,
    completed_not_submitted_acps: 0,
    not_started_acps: 0,
    stale_records_count: 0,
  };

  const completionDistData = analytics?.completion_distribution || [
    { range: "0–25%", count: 0 },
    { range: "26–50%", count: 0 },
    { range: "51–75%", count: 0 },
    { range: "76–99%", count: 0 },
    { range: "100%", count: 0 },
  ];

  const reviewStatusData = (analytics?.review_status_distribution || [])
    .filter((item: any) => item.count > 0)
    .map((item: any) => {
      let color = AMBER_WARNING;
      if (item.status === "Reviewed") color = EMERALD_SUCCESS;
      else if (item.status === "Pending Review") color = AMBER_WARNING;
      else if (item.status === "Completed – Not Submitted") color = TEAL_PRIMARY;
      else if (item.status === "In Progress") color = BLUE_ACCENT;
      else if (item.status === "Not Started") color = SLATE_MUTED;
      return { ...item, color };
    });

  const workflowStatusBreakdown = (analytics?.review_status_distribution || []).map((item: any) => {
    let color = BLUE_ACCENT;
    if (item.status === "Reviewed") color = EMERALD_SUCCESS;
    else if (item.status === "Pending Review") color = AMBER_WARNING;
    else if (item.status === "Completed – Not Submitted") color = TEAL_PRIMARY;
    else if (item.status === "Not Started") color = SLATE_MUTED;
    return { ...item, color };
  });

  const sectionCompletionData = analytics?.section_completion || [];

  const recentActivities = useMemo(() => {
    const list = analytics?.recent_activities || [];
    if (statusFilter === "all") return list;
    return list.filter((act: any) => act.status === statusFilter);
  }, [analytics?.recent_activities, statusFilter]);

  const insights = analytics?.insights || {
    awaiting_review: 0,
    in_progress: 0,
    reviewed: 0,
    not_started: 0,
    stale_records: 0,
  };

  const statCards = [
    {
      label: "Total Assigned Patients",
      value: summary.total_patients,
      subtext: "In clinical patient registry",
      icon: Users,
      tone: "bg-primary/10 text-primary",
    },
    {
      label: "Pending Reviews",
      value: summary.pending_reviews,
      subtext: "Awaiting clinical acknowledgement",
      icon: Clock,
      tone: "bg-amber-500/10 text-amber-600",
    },
    {
      label: "Reviewed ACPs",
      value: summary.reviewed_acps,
      subtext: "Clinically acknowledged & approved",
      icon: ShieldCheck,
      tone: "bg-emerald-500/10 text-emerald-600",
    },
    {
      label: "In Progress Drafts",
      value: summary.in_progress_acps + summary.completed_not_submitted_acps,
      subtext: "Patients currently drafting ACP",
      icon: FileText,
      tone: "bg-blue-500/10 text-blue-600",
    },
  ];

  return (
    <DoctorPageShell>
      {/* Header with Title and Global Filters */}
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
            Clinical ACP Analytics & Insights
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Real-time population health metrics and advance care planning progress across all assigned patients.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Select value={dateFilter} onValueChange={setDateFilter}>
            <SelectTrigger className="h-9 w-[130px] rounded-xl text-xs">
              <Calendar className="mr-1.5 h-3.5 w-3.5 text-muted-foreground" />
              <SelectValue placeholder="Date range" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Time</SelectItem>
              <SelectItem value="30d">Last 30 Days</SelectItem>
              <SelectItem value="7d">Last 7 Days</SelectItem>
            </SelectContent>
          </Select>

          <Button
            variant="outline"
            size="sm"
            className="h-9 rounded-xl text-xs gap-1.5"
            onClick={() => refetch()}
            title="Refresh analytics data"
          >
            <RefreshCw className={cn("h-3.5 w-3.5", isRefetching && "animate-spin text-primary")} />
            Refresh
          </Button>
        </div>
      </header>

      {/* 1. Four Summary Statistic Cards */}
      <section className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {statCards.map((card) => {
          const Icon = card.icon;
          return (
            <MotionCard key={card.label} className="p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    {card.label}
                  </p>
                  <p className="mt-1 text-3xl font-bold tracking-tight text-foreground">
                    {isLoading ? "…" : card.value}
                  </p>
                </div>
                <div className={cn("grid h-11 w-11 place-items-center rounded-xl", card.tone)}>
                  <Icon className="h-5 w-5" />
                </div>
              </div>
              <p className="mt-3 text-xs text-muted-foreground">{card.subtext}</p>
            </MotionCard>
          );
        })}
      </section>

      {/* 2. Visualizations Row 1: ACP Completion Distribution & Status Donut */}
      <section className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* A. ACP Completion Distribution */}
        <MotionCard className="lg:col-span-7 p-5">
          <div className="flex items-center justify-between border-b border-border pb-4">
            <div>
              <h2 className="text-base font-bold text-foreground flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-primary" />
                ACP Completion Distribution
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Number of patients grouped by genuine ACP completion percentage
              </p>
            </div>
            <Badge variant="outline" className="text-[11px] font-medium rounded-full">
              {summary.total_patients} Patients
            </Badge>
          </div>

          <div className="mt-6 h-[260px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={completionDistData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.2} />
                <XAxis dataKey="range" tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} />
                <Tooltip
                  formatter={(val: any) => [`${val} Patients`, "Count"]}
                  contentStyle={{
                    borderRadius: "12px",
                    border: "1px solid #e2e8f0",
                    boxShadow: "0 4px 12px rgba(0,0,0,0.06)",
                    fontSize: "12px",
                  }}
                />
                <Bar dataKey="count" radius={[8, 8, 0, 0]}>
                  {completionDistData.map((entry: any, index: number) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={entry.range === "100%" ? EMERALD_SUCCESS : entry.range === "0–25%" ? "#94a3b8" : TEAL_PRIMARY}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </MotionCard>

        {/* B. ACP Review Status Donut Chart */}
        <MotionCard className="lg:col-span-5 p-5">
          <div className="flex items-center justify-between border-b border-border pb-4">
            <div>
              <h2 className="text-base font-bold text-foreground flex items-center gap-2">
                <PieIcon className="h-4 w-4 text-primary" />
                ACP Workflow Status
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Clinical review & acknowledgement breakdown
              </p>
            </div>
          </div>

          <div className="mt-4 flex h-[260px] w-full items-center justify-center">
            {reviewStatusData.length === 0 ? (
              <p className="text-xs text-muted-foreground">No review status records to display.</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={reviewStatusData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={88}
                    paddingAngle={4}
                    dataKey="count"
                    nameKey="status"
                  >
                    {reviewStatusData.map((entry: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(val: any, name: any) => [`${val} Patients`, name]}
                    contentStyle={{
                      borderRadius: "12px",
                      border: "1px solid #e2e8f0",
                      fontSize: "12px",
                    }}
                  />
                  <Legend verticalAlign="bottom" height={36} iconType="circle" wrapperStyle={{ fontSize: "11px" }} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </MotionCard>
      </section>

      {/* 3. Visualizations Row 2: Section Completion & Workflow Status Breakdown */}
      <section className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* D. ACP Section Completion Horizontal Bar Chart */}
        <MotionCard className="lg:col-span-7 p-5">
          <div className="flex items-center justify-between border-b border-border pb-4">
            <div>
              <h2 className="text-base font-bold text-foreground flex items-center gap-2">
                <Activity className="h-4 w-4 text-primary" />
                ACP Section Completion Rates
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Average completion percentage across the 6 clinical ACP sections
              </p>
            </div>
          </div>

          <div className="mt-6 h-[270px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                layout="vertical"
                data={sectionCompletionData}
                margin={{ top: 5, right: 30, left: 40, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" horizontal={false} opacity={0.2} />
                <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11, fill: "#64748b" }} unit="%" />
                <YAxis dataKey="section" type="category" tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} width={110} />
                <Tooltip
                  formatter={(val: any) => [`${val}% Average Completion`, "Completion"]}
                  contentStyle={{
                    borderRadius: "12px",
                    border: "1px solid #e2e8f0",
                    fontSize: "12px",
                  }}
                />
                <Bar dataKey="completion" radius={[0, 6, 6, 0]} fill={TEAL_LIGHT} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </MotionCard>

        {/* C. Clinical Workflow Status Breakdown */}
        <MotionCard className="lg:col-span-5 p-5">
          <div className="flex items-center justify-between border-b border-border pb-4">
            <div>
              <h2 className="text-base font-bold text-foreground flex items-center gap-2">
                <ClipboardList className="h-4 w-4 text-primary" />
                Clinical Workflow Statuses
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Breakdown across all 5 distinct stages
              </p>
            </div>
          </div>

          <div className="mt-4 space-y-3">
            {workflowStatusBreakdown.map((item: any) => {
              const total = summary.total_patients || 1;
              const pct = Math.round((item.count / total) * 100);
              return (
                <div key={item.status} className="rounded-xl border border-border p-3 bg-surface/40">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.color }} />
                      <span className="text-xs font-semibold text-foreground">{item.status}</span>
                    </div>
                    <div className="text-right">
                      <span className="text-sm font-bold text-foreground">{item.count}</span>
                      <span className="text-[11px] text-muted-foreground ml-1">({pct}%)</span>
                    </div>
                  </div>
                  <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-border/50">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{ width: `${pct}%`, backgroundColor: item.color }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </MotionCard>
      </section>

      {/* 4. Row 3: Patient Insights & Recent Patient Activity */}
      <section className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* F. Patient Insights */}
        <MotionCard className="lg:col-span-4 p-5">
          <div className="border-b border-border pb-4">
            <h2 className="text-base font-bold text-foreground flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              Patient Care Insights
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Automated clinical takeaways from live database records
            </p>
          </div>

          <div className="mt-4 space-y-3">
            <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3.5">
              <div className="flex items-start gap-3">
                <Clock className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <p className="text-xs font-bold text-amber-900 dark:text-amber-200">
                    {insights.awaiting_review} Completed Plan{insights.awaiting_review === 1 ? "" : "s"} Awaiting Review
                  </p>
                  <p className="text-[11px] text-amber-700/80 dark:text-amber-300/80 mt-0.5">
                    Patients have finalized their advance care preferences and require clinical acknowledgement.
                  </p>
                </div>
              </div>
            </div>

            <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-3.5">
              <div className="flex items-start gap-3">
                <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0 mt-0.5" />
                <div>
                  <p className="text-xs font-bold text-emerald-900 dark:text-emerald-200">
                    {insights.reviewed} Reviewed & Approved Directives
                  </p>
                  <p className="text-[11px] text-emerald-700/80 dark:text-emerald-300/80 mt-0.5">
                    Advance care plans with official clinical sign-off from your care team.
                  </p>
                </div>
              </div>
            </div>

            <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-3.5">
              <div className="flex items-start gap-3">
                <FileText className="h-5 w-5 text-blue-600 shrink-0 mt-0.5" />
                <div>
                  <p className="text-xs font-bold text-blue-900 dark:text-blue-200">
                    {insights.in_progress} In-Progress Draft{insights.in_progress === 1 ? "" : "s"}
                  </p>
                  <p className="text-[11px] text-blue-700/80 dark:text-blue-300/80 mt-0.5">
                    Patients actively drafting their directives who may need care-team guidance.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </MotionCard>

        {/* E. Recent Patient Activity Table */}
        <MotionCard className="lg:col-span-8 p-0 overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border p-5">
            <div>
              <h2 className="text-base font-bold text-foreground flex items-center gap-2">
                <Activity className="h-4 w-4 text-primary" />
                Recent Patient Activity
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Audit trail of recent patient submissions, reviews, and clinical changes
              </p>
            </div>

            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="h-8 w-[150px] rounded-lg text-xs">
                <Filter className="mr-1 h-3 w-3 text-muted-foreground" />
                <SelectValue placeholder="Filter status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All statuses</SelectItem>
                <SelectItem value="Pending Review">Pending Review</SelectItem>
                <SelectItem value="Reviewed">Reviewed</SelectItem>
                <SelectItem value="In Progress">In Progress</SelectItem>
                <SelectItem value="Not Started">Not Started</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="border-border hover:bg-transparent">
                  <TableHead className="text-[11px] font-semibold uppercase text-muted-foreground">
                    Patient
                  </TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase text-muted-foreground">
                    Action / Event
                  </TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase text-muted-foreground">
                    Timestamp
                  </TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase text-muted-foreground">
                    Current Status
                  </TableHead>
                  <TableHead className="text-right text-[11px] font-semibold uppercase text-muted-foreground">
                    Dossier
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recentActivities.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="h-32 text-center text-xs text-muted-foreground">
                      No recent patient activities recorded yet.
                    </TableCell>
                  </TableRow>
                ) : (
                  recentActivities.map((act: any) => {
                    let dateStr = "—";
                    if (act.timestamp) {
                      try {
                        const d = new Date(act.timestamp);
                        dateStr = d.toLocaleDateString("en-US", {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        });
                      } catch {
                        dateStr = "—";
                      }
                    }

                    return (
                      <TableRow key={act.id} className="border-border hover:bg-surface/50 transition-colors">
                        <TableCell>
                          <button
                            type="button"
                            onClick={() =>
                              act.patient_id &&
                              navigate({
                                to: "/doctor-dashboard/patients/$patientId",
                                params: { patientId: String(act.patient_id) },
                              })
                            }
                            className="font-bold text-xs text-foreground hover:text-primary transition-colors cursor-pointer text-left"
                          >
                            {act.patient_name}
                          </button>
                        </TableCell>
                        <TableCell className="text-xs text-foreground">
                          {act.action}
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                          {dateStr}
                        </TableCell>
                        <TableCell>
                          <Badge className={cn("rounded-full border px-2 py-0 text-[10px]", statusStyle(act.status))}>
                            {act.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          {act.patient_id && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 text-[11px] text-primary gap-1 p-1 hover:bg-primary/10 rounded-lg"
                              onClick={() =>
                                navigate({
                                  to: "/doctor-dashboard/patients/$patientId",
                                  params: { patientId: String(act.patient_id) },
                                })
                              }
                            >
                              View <ArrowUpRight className="h-3 w-3" />
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </div>
        </MotionCard>
      </section>
    </DoctorPageShell>
  );
}
