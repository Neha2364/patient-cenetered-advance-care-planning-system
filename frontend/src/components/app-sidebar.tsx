import { Link, useRouterState } from "@tanstack/react-router";
import {
  LayoutDashboard,
  MessageSquare,
  FileText,
  Settings,
  LogOut,
  HeartPulse,
  Users,
  ClipboardCheck,
  BarChart3,
  type LucideIcon,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { authService } from "@/lib/api";

type NavItem = { title: string; url: string; icon: LucideIcon };

const patientNav: NavItem[] = [
  { title: "Dashboard", url: "/patient-dashboard", icon: LayoutDashboard },
  { title: "ACP Chatbot", url: "/patient-dashboard/chat", icon: MessageSquare },
  { title: "My Documents", url: "/patient-dashboard/documents", icon: FileText },
  { title: "Settings", url: "/patient-dashboard/settings", icon: Settings },
];

const doctorNav: NavItem[] = [
  { title: "Dashboard", url: "/doctor-dashboard", icon: LayoutDashboard },
  { title: "My Patients", url: "/doctor-dashboard/patients", icon: Users },
  { title: "ACP Reviews", url: "/doctor-dashboard/reviews", icon: ClipboardCheck },
  { title: "Analytics", url: "/doctor-dashboard/analytics", icon: BarChart3 },
  { title: "Settings", url: "/doctor-dashboard/settings", icon: Settings },
];

export function BrandLogo({ compact = false }: { compact?: boolean }) {
  return (
    <Link to="/" className="flex items-center gap-3">
      <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-brand-gradient text-white shadow-md">
        <HeartPulse className="h-5 w-5" />
      </div>
      {!compact && (
        <div className="min-w-0">
          <div className="text-[15px] font-bold leading-tight text-foreground">ACP Care</div>
          <div className="truncate text-[11px] font-medium text-muted-foreground">
            Advance Care Planning
          </div>
        </div>
      )}
    </Link>
  );
}

export function AppSidebar({
  role,
  user,
}: {
  role: "patient" | "doctor";
  user: { name: string; email: string; initial: string };
}) {
  const currentPath = useRouterState({ select: (r) => r.location.pathname });
  const items = role === "patient" ? patientNav : doctorNav;
  const roleLabel = role === "patient" ? "PATIENT" : "DOCTOR";

  return (
    <aside className="sticky top-0 hidden h-screen w-[240px] shrink-0 flex-col border-r border-border bg-white lg:flex">
      <div className="px-5 pb-4 pt-6">
        <BrandLogo />
      </div>

      <div className="mx-4 mb-4 rounded-2xl border border-border bg-surface p-3">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-brand-gradient text-sm font-semibold text-white">
            {user.initial}
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-semibold text-foreground">{user.name}</div>
            <div className="truncate text-[11px] text-muted-foreground">{user.email}</div>
          </div>
        </div>
        <Badge
          variant="outline"
          className="mt-3 border-primary/30 bg-primary/5 text-[10px] font-semibold tracking-wider text-primary"
        >
          {roleLabel}
        </Badge>
      </div>

      <nav className="flex-1 space-y-1 px-3">
        {items.map((item) => {
          const active = currentPath === item.url;
          return (
            <Link
              key={item.title}
              to={item.url as never}
              className={cn(
                "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all",
                active
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:bg-surface hover:text-foreground",
              )}
            >
              <item.icon className={cn("h-4 w-4 shrink-0", active ? "text-white" : "")} />
              <span className="truncate">{item.title}</span>
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto px-3 pb-6 pt-4">
        <div className="mx-1 mb-3 h-px bg-border" />
        <Link
          to="/"
          onClick={() => authService.logout()}
          className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-destructive/5 hover:text-destructive"
        >
          <LogOut className="h-4 w-4" />
          Logout
        </Link>
      </div>
    </aside>
  );
}
