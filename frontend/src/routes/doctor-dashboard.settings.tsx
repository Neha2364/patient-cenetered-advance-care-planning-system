import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { LogOut, Mail, ShieldCheck, UserRound, KeyRound, ChevronRight } from "lucide-react";
import { DoctorPageShell } from "@/components/doctor-page-shell";
import { MotionCard } from "@/components/motion-card";
import { Button } from "@/components/ui/button";
import { authService } from "@/lib/api";

export const Route = createFileRoute("/doctor-dashboard/settings")({ component: SettingsPage });

function SettingsPage() {
  const navigate = useNavigate();
  const user = authService.getCurrentUser();
  const fields = [
    { icon: UserRound, label: "Name", value: user?.full_name || "Doctor" },
    { icon: Mail, label: "Email", value: user?.email || "Not available" },
    { icon: ShieldCheck, label: "Role", value: "Doctor" },
  ];

  return (
    <DoctorPageShell>
      <header>
        <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Your doctor account details and security settings.
        </p>
      </header>

      <div className="mt-6 max-w-2xl space-y-6">
        {/* Profile Card */}
        <MotionCard>
          <h2 className="text-base font-semibold text-foreground mb-2">Doctor Profile</h2>
          <div className="divide-y divide-border">
            {fields.map(({ icon: Icon, label, value }) => (
              <div key={label} className="flex items-center gap-4 py-4">
                <div className="grid h-10 w-10 place-items-center rounded-xl bg-primary/10 text-primary">
                  <Icon className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">{label}</p>
                  <p className="mt-0.5 font-medium text-foreground">{value}</p>
                </div>
              </div>
            ))}
          </div>
        </MotionCard>

        {/* Security & Password Card */}
        <MotionCard>
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-4">
              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-amber-500/10 text-amber-600">
                <KeyRound className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-base font-semibold text-foreground">Password & Security</h2>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  Update your clinician account password at any time to ensure platform security.
                </p>
              </div>
            </div>
            <Button asChild variant="outline" className="shrink-0 rounded-xl">
              <Link to="/doctor-dashboard/change-password">
                Change Password
                <ChevronRight className="ml-1.5 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </MotionCard>

        {/* Sign Out Card */}
        <MotionCard>
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-foreground">Session Management</h2>
              <p className="text-xs text-muted-foreground">
                Sign out of your active clinician session on this browser.
              </p>
            </div>
            <Button
              variant="outline"
              className="rounded-xl text-destructive hover:text-destructive hover:bg-destructive/10"
              onClick={() => {
                authService.logout();
                navigate({ to: "/doctor-login" });
              }}
            >
              <LogOut className="mr-2 h-4 w-4" />
              Logout
            </Button>
          </div>
        </MotionCard>
      </div>
    </DoctorPageShell>
  );
}
