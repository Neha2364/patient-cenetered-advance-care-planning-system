import { type ReactNode, useMemo } from "react";
import { Link, useRouterState } from "@tanstack/react-router";
import {
  LayoutDashboard,
  Users,
  UserPlus,
  ClipboardList,
  Settings,
  LogOut,
  HeartPulse,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { authService } from "@/lib/api";
import { RequireAuthentication } from "@/components/require-authentication";

type AdminRoutePath =
  | "/admin-dashboard"
  | "/admin-dashboard/doctors"
  | "/admin-dashboard/doctors/add"
  | "/admin-dashboard/patients"
  | "/admin-dashboard/settings";

type NavItem = {
  title: string;
  url: AdminRoutePath;
  icon: LucideIcon;
};

const adminNav: NavItem[] = [
  { title: "Dashboard", url: "/admin-dashboard", icon: LayoutDashboard },
  { title: "Manage Doctors", url: "/admin-dashboard/doctors", icon: Users },
  { title: "Add Doctor", url: "/admin-dashboard/doctors/add", icon: UserPlus },
  { title: "Manage Patients", url: "/admin-dashboard/patients", icon: ClipboardList },
  { title: "Account Settings", url: "/admin-dashboard/settings", icon: Settings },
];

function AdminSidebar({ user }: { user: { name: string; email: string; initial: string } }) {
  const currentPath = useRouterState({ select: (r) => r.location.pathname });

  return (
    <aside className="sticky top-0 hidden h-screen w-[240px] shrink-0 flex-col border-r border-border bg-white lg:flex">
      <div className="px-5 pb-4 pt-6">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-brand-gradient text-white shadow-md">
            <HeartPulse className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <div className="text-[15px] font-bold leading-tight text-foreground">ACP Care</div>
            <div className="truncate text-[11px] font-medium text-muted-foreground">
              Admin Portal
            </div>
          </div>
        </div>
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
          <ShieldCheck className="mr-1 h-3 w-3" />
          ADMINISTRATOR
        </Badge>
      </div>

      <nav className="flex-1 space-y-1 px-3">
        {adminNav.map((item) => {
          const active =
            item.url === "/admin-dashboard/doctors"
              ? currentPath === "/admin-dashboard/doctors" ||
                currentPath === "/admin-dashboard/doctors/" ||
                (currentPath.startsWith("/admin-dashboard/doctors/") &&
                  !currentPath.startsWith("/admin-dashboard/doctors/add"))
              : item.url === "/admin-dashboard"
                ? currentPath === "/admin-dashboard" || currentPath === "/admin-dashboard/"
                : currentPath === item.url || currentPath.startsWith(item.url + "/");
          return (
            <Link
              key={item.title}
              to={item.url}
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
          to="/admin-login"
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

export function AdminShell({ children }: { children: ReactNode }) {
  const currentUser = authService.getCurrentUser();
  const admin = useMemo(() => {
    const name = currentUser?.full_name || "Administrator";
    return { name, email: currentUser?.email || "", initial: name.charAt(0).toUpperCase() };
  }, [currentUser]);

  return (
    <RequireAuthentication allowedRoles={["admin"]}>
      <div className="flex min-h-screen w-full bg-surface">
        <AdminSidebar user={admin} />
        <main className="mx-auto w-full max-w-[1600px] flex-1 px-5 py-6 lg:px-8 lg:py-8">
          {children}
        </main>
      </div>
    </RequireAuthentication>
  );
}
