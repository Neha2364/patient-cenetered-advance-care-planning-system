import { createFileRoute, Outlet, useRouterState } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import {
  Users,
  ClipboardCheck,
  Loader2,
  AlertTriangle,
  Bell,
  Download,
  Search,
  RefreshCw,
  Menu,
  Eye,
  CheckCheck,
  MessageSquare,
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

export const Route = createFileRoute("/doctor-dashboard")({
  head: () => ({
    meta: [
      { title: "Doctor Dashboard — ACP Care" },
      {
        name: "description",
        content:
          "Monitor patient ACP progress, review submissions, and manage access requests in one place.",
      },
    ],
  }),
  component: DoctorDashboardLayout,
});

function DoctorDashboardLayout() {
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  return pathname === "/doctor-dashboard" ? <DoctorDashboard /> : <Outlet />;
}
const sectionCompletion = [
  { label: "Personal Information", value: 100 },
  { label: "Medical Preferences", value: 85 },
  { label: "End-of-Life", value: 60 },
  { label: "Proxy", value: 45 },
  { label: "Donation", value: 30 },
  { label: "Review", value: 15 },
];

function DoctorDashboard() {
  const currentUser = authService.getCurrentUser();
  if (!currentUser) return <RequireAuthentication>{null}</RequireAuthentication>;

  const doctor = useMemo(() => {
    return {
      name: currentUser?.full_name || "Doctor",
      email: currentUser?.email || "doctor@acpcare.app",
      initial: (currentUser?.full_name || "D").charAt(0).toUpperCase(),
    };
  }, [currentUser]);

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const { data: rawPatients = [], refetch } = useQuery({
    queryKey: ["doctorPatients", search, statusFilter],
    queryFn: () => doctorService.getPatients({ 
      search: search || undefined, 
      review_status: statusFilter !== "all" ? statusFilter : undefined 
    }),
  });

  const patients = useMemo(() => {
    return rawPatients.map((p: any) => ({
      name: p.full_name,
      initial: p.full_name?.charAt(0).toUpperCase() || "P",
      age: p.age || 0,
      completion: p.is_completed ? 100 : (p.review_status !== "Pending Review" ? 50 : 20),
      status: p.review_status,
      priority: p.review_status === "Pending Review" ? "High" : "Low",
      updated: new Date().toLocaleDateString(),
      id: p.patient_id,
    }));
  }, [rawPatients]);

  const stats = useMemo(() => {
    const total = patients.length;
    const completed = patients.filter((p: any) => p.status === "Reviewed" || p.status === "Completed").length;
    const inProgress = patients.filter((p: any) => p.status === "Pending Review" || p.status === "In Progress").length;
    const highPriority = patients.filter((p: any) => p.priority === "High").length;
    
    return [
      { title: "Total Patients", value: total.toString(), desc: "Assigned to you", icon: Users, tone: "primary" },
      { title: "ACPs Complete", value: completed.toString(), desc: "Reviewed submissions", icon: ClipboardCheck, tone: "success" },
      { title: "In Progress", value: inProgress.toString(), desc: "Awaiting review", icon: Loader2, tone: "info" },
      { title: "High Priority", value: highPriority.toString(), desc: "Needs immediate review", icon: AlertTriangle, tone: "danger" },
    ];
  }, [patients]);

  const priorityDistribution = useMemo(() => {
    const total = patients.length || 1;
    const completed = patients.filter((p: any) => p.status === "Reviewed" || p.status === "Completed").length;
    const pending = patients.filter((p: any) => p.status === "Pending Review").length;
    const other = patients.length - completed - pending;
    
    return {
      totalPatients: patients.length,
      completed: Math.round((completed / total) * 100) || 0,
      pending: Math.round((other / total) * 100) || 0,
      high: Math.round((pending / total) * 100) || 0,
    };
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

          <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
            <PatientTable 
              patients={patients} 
              search={search} 
              setSearch={setSearch} 
              statusFilter={statusFilter} 
              setStatusFilter={setStatusFilter}
              refetch={refetch}
            />
            <aside className="flex flex-col gap-6">
              <SectionCompletionCard />
              <PriorityDonutCard distribution={priorityDistribution} />
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
      <Button variant="ghost" size="icon" className="rounded-xl">
        <Bell className="h-5 w-5" />
      </Button>
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
          Monitor patient ACP progress and review submissions.
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <Badge
          variant="outline"
          className="hidden rounded-full border-border bg-white px-3 py-1 text-[11px] font-medium text-muted-foreground md:inline-flex"
        >
          Live Updates
        </Badge>
        <Button variant="outline" className="hidden h-10 rounded-xl text-sm md:inline-flex">
          <Download className="mr-2 h-4 w-4" /> Export Report
        </Button>
        <Button variant="outline" size="icon" className="hidden rounded-xl lg:inline-flex">
          <Bell className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}

const toneStyles: Record<string, string> = {
  primary: "bg-primary/10 text-primary",
  success: "bg-success/10 text-success",
  info: "bg-[color:var(--accent-blue)]/10 text-[color:var(--accent-blue)]",
  danger: "bg-danger/10 text-danger",
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
  return s === "Completed" || s === "Reviewed"
    ? "border-success/25 bg-success/10 text-success"
    : s === "In Progress"
      ? "border-[color:var(--accent-blue)]/25 bg-[color:var(--accent-blue)]/10 text-[color:var(--accent-blue)]"
      : "border-warning/25 bg-warning/10 text-warning";
}
function priorityStyle(p: string) {
  return p === "High"
    ? "border-danger/25 bg-danger/10 text-danger"
    : p === "Medium"
      ? "border-warning/25 bg-warning/10 text-warning"
      : "border-border bg-surface text-muted-foreground";
}

function PatientTable({ patients, search, setSearch, statusFilter, setStatusFilter, refetch }: any) {
  const handleReview = async (patientId: number, status: string) => {
    try {
      await doctorService.reviewPatientACP(patientId, status);
      refetch();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <MotionCard className="p-0">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border p-5">
        <div className="min-w-0">
          <h2 className="text-lg font-bold text-foreground">Patient ACP Records</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {patients.length} patients found
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input 
              placeholder="Search patients" 
              className="h-10 w-[220px] rounded-xl pl-9" 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="h-10 w-[140px] rounded-xl">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="Reviewed">Reviewed</SelectItem>
              <SelectItem value="In Progress">In Progress</SelectItem>
              <SelectItem value="Pending Review">Pending</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="icon" className="h-10 w-10 rounded-xl" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4" />
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
                Completion
              </TableHead>
              <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Status
              </TableHead>
              <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Priority
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
            {patients.map((p: any, i: number) => (
              <motion.tr
                key={p.id}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.03 * i, duration: 0.3 }}
                className="border-border transition-colors hover:bg-surface"
              >
                <TableCell>
                  <div className="flex items-center gap-3">
                    <div className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-brand-gradient text-xs font-semibold text-white">
                      {p.initial}
                    </div>
                    <div className="min-w-0">
                      <div className="truncate text-sm font-semibold text-foreground">{p.name}</div>
                      <div className="text-[11px] text-muted-foreground">Patient #{p.id}</div>
                    </div>
                  </div>
                </TableCell>
                <TableCell className="text-sm text-foreground">{p.age}</TableCell>
                <TableCell>
                  <div className="flex w-[160px] items-center gap-2">
                    <Progress value={p.completion} className="h-1.5 flex-1" />
                    <span className="text-xs font-medium text-muted-foreground">{p.completion}%</span>
                  </div>
                </TableCell>
                <TableCell>
                  <Badge className={cn("rounded-full border px-2.5 py-0.5 text-[11px] font-medium", statusStyle(p.status))}>
                    {p.status}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge className={cn("rounded-full border px-2.5 py-0.5 text-[11px] font-medium", priorityStyle(p.priority))}>
                    {p.priority}
                  </Badge>
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">{p.updated}</TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-1">
                    <Button variant="ghost" size="icon" className="h-8 w-8 rounded-lg" aria-label="View">
                      <Eye className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8 rounded-lg" aria-label="Review">
                      <MessageSquare className="h-4 w-4" />
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      className="h-8 w-8 rounded-lg text-success" 
                      aria-label="Approve"
                      onClick={() => handleReview(p.id, "Reviewed")}
                    >
                      <CheckCheck className="h-4 w-4" />
                    </Button>
                  </div>
                </TableCell>
              </motion.tr>
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between border-t border-border px-5 py-3">
        <p className="text-xs text-muted-foreground">Page 1 of 1</p>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="h-8 rounded-lg text-xs" disabled>
            Previous
          </Button>
          <Button size="sm" className="h-8 rounded-lg bg-primary text-xs hover:bg-primary/90" disabled>
            Next
          </Button>
        </div>
      </div>
    </MotionCard>
  );
}

function SectionCompletionCard() {
  return (
    <MotionCard>
      <h3 className="text-sm font-bold text-foreground">Section Completion</h3>
      <p className="mt-0.5 text-[11px] text-muted-foreground">Average completion across patients</p>
      <div className="mt-5 space-y-4">
        {sectionCompletion.map((s, i) => (
          <div key={s.label}>
            <div className="mb-1.5 flex items-center justify-between">
              <span className="text-xs font-medium text-foreground">{s.label}</span>
              <span className="text-xs font-semibold text-muted-foreground">{s.value}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-surface">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${s.value}%` }}
                transition={{ duration: 0.7, delay: 0.05 * i, ease: "easeOut" }}
                className="h-full rounded-full bg-brand-gradient"
              />
            </div>
          </div>
        ))}
      </div>
    </MotionCard>
  );
}

function PriorityDonutCard({ distribution }: { distribution: any }) {
  const { completed, pending, high, totalPatients } = distribution;
  const hasData = completed + pending + high > 0;
  const gradient = hasData
    ? `conic-gradient(oklch(0.68 0.15 155) 0 ${completed}%, oklch(0.78 0.15 75) ${completed}% ${completed + pending}%, oklch(0.63 0.22 27) ${completed + pending}% 100%)`
    : "conic-gradient(var(--surface) 0 100%)";
  const legend = [
    { label: "Completed", value: completed, color: "bg-success" },
    { label: "Pending", value: pending, color: "bg-warning" },
    { label: "High Priority", value: high, color: "bg-danger" },
  ];
  return (
    <MotionCard>
      <h3 className="text-sm font-bold text-foreground">ACP Priority Distribution</h3>
      <p className="mt-0.5 text-[11px] text-muted-foreground">Across all active patients</p>
      <div className="mt-5 flex items-center gap-6">
        <div
          className="relative h-32 w-32 shrink-0 rounded-full"
          style={{ background: gradient }}
          aria-hidden
        >
          <div className="absolute inset-3 grid place-items-center rounded-full bg-card">
            <div className="text-center">
              <div className="text-xl font-bold text-foreground">{totalPatients}</div>
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Patients</div>
            </div>
          </div>
        </div>
        <ul className="min-w-0 flex-1 space-y-2.5">
          {legend.map((l) => (
            <li key={l.label} className="flex items-center gap-2 text-xs">
              <span className={cn("h-2.5 w-2.5 shrink-0 rounded-sm", l.color)} />
              <span className="min-w-0 flex-1 truncate text-foreground">{l.label}</span>
              <span className="font-semibold text-muted-foreground">{l.value}%</span>
            </li>
          ))}
        </ul>
      </div>
    </MotionCard>
  );
}
