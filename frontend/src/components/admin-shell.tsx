import { type ReactNode, useMemo, useState } from "react";
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
  Menu,
  type LucideIcon,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
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

function AdminSidebarContent({
  user,
  onNavigate,
}: {
  user: { name: string; email: string; initial: string };
  onNavigate?: () => void;
}) {
  const currentPath = useRouterState({ select: (r) => r.location.pathname });

  return (
    <div className="flex h-full flex-col bg-white">
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
              onClick={onNavigate}
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
          onClick={() => {
            onNavigate?.();
            authService.logout();
          }}
          className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-destructive/5 hover:text-destructive"
        >
          <LogOut className="h-4 w-4" />
          Logout
        </Link>
      </div>
    </div>
  );
}

function AdminSidebar({ user }: { user: { name: string; email: string; initial: string } }) {
  return (
    <aside className="sticky top-0 hidden h-screen w-[240px] shrink-0 border-r border-border bg-white lg:flex lg:flex-col">
      <AdminSidebarContent user={user} />
    </aside>
  );
}

function AdminMobileHeader({ user }: { user: { name: string; email: string; initial: string } }) {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between border-b border-border bg-white/90 px-4 py-3 backdrop-blur lg:hidden">
      <div className="flex items-center gap-2">
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="h-9 w-9 rounded-xl">
              <Menu className="h-5 w-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-[260px] p-0">
            <AdminSidebarContent user={user} onNavigate={() => setOpen(false)} />
          </SheetContent>
        </Sheet>
        <div className="flex items-center gap-2">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-brand-gradient text-white shadow-sm">
            <HeartPulse className="h-4 w-4" />
          </div>
          <span className="text-sm font-bold text-foreground">ACP Care Admin</span>
        </div>
      </div>
      <Badge variant="outline" className="border-primary/30 bg-primary/5 text-[10px] font-semibold text-primary">
        ADMIN
      </Badge>
    </header>
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
      <div className="flex min-h-screen w-full flex-col bg-surface lg:flex-row">
        <AdminMobileHeader user={admin} />
        <AdminSidebar user={admin} />
        <main className="min-w-0 w-full flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          {children}
        </main>
      </div>
    </RequireAuthentication>
  );
}
