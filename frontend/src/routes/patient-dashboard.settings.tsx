import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { LogOut, Mail, Phone, Languages, User } from "lucide-react";
import { PatientShell } from "@/components/patient-shell";
import { MotionCard } from "@/components/motion-card";
import { Button } from "@/components/ui/button";
import { authService, patientService } from "@/lib/api";

export const Route = createFileRoute("/patient-dashboard/settings")({ component: SettingsPage });
function SettingsPage() {
  const navigate = useNavigate();
  const currentUser = authService.getCurrentUser();
  const { data: profile, isLoading } = useQuery({ queryKey: ["patientProfile"], queryFn: patientService.getProfile });
  const fields = [{ icon: User, label: "Display Name", value: profile?.full_name || currentUser?.full_name }, { icon: Mail, label: "Email", value: profile?.email || currentUser?.email }, { icon: Phone, label: "Phone Number", value: profile?.phone || "Not provided" }, { icon: Languages, label: "Preferred Language", value: profile?.preferred_language || "English" }];
  return <PatientShell><header><h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">Settings</h1><p className="mt-1 text-sm text-muted-foreground">Your account and communication details.</p></header><MotionCard className="mt-6 max-w-2xl"><div className="divide-y divide-border">{isLoading ? <p className="py-6 text-sm text-muted-foreground">Loading settings�</p> : fields.map(({ icon: Icon, label, value }) => <div key={label} className="flex items-center gap-4 py-5"><div className="grid h-10 w-10 place-items-center rounded-xl bg-primary/10 text-primary"><Icon className="h-5 w-5" /></div><div><p className="text-xs text-muted-foreground">{label}</p><p className="mt-0.5 font-medium text-foreground">{value}</p></div></div>)}</div><Button variant="outline" className="mt-6 rounded-xl text-destructive hover:text-destructive" onClick={() => { authService.logout(); navigate({ to: "/" }); }}><LogOut className="mr-2 h-4 w-4" />Logout</Button></MotionCard></PatientShell>;
}